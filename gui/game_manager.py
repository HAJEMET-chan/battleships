# gui/game_manager.py
from typing import Dict, List, Tuple, Any, Optional
from src.api import create_new_game, place_ship, validate_full_battlefield
from src.main import BattleField, VERTICAL_KEYS, HORIZONTAL_KEYS # Импортируем для логики расстановки

class GameManager:
    """
    Управляет состоянием игры и логикой, специфичной для GUI,
    такой как отслеживание текущих выбранных клеток для расстановки кораблей
    и проверка правил расстановки.
    """
    def __init__(self):
        self.battlefields: Dict[str, BattleField] = {}
        self.current_player_placement_coords: Dict[str, List[Tuple[str, str]]] = {}
        self.game_phase: str = "setup" # "setup", "placement", "pre_game_ready", "in_progress", "game_over", "network_setup"

        # Определяем количество кораблей каждого типа для стандартного Морского боя
        # 4-палубный, 3-палубный (x2), 2-палубный (x3), 1-палубный (x4)
        self.ship_lengths_to_place = {
            4: 1, # Один 4-клеточный корабль
            3: 2, # Два 3-клеточных корабля
            2: 3, # Три 2-клеточных корабля
            1: 4  # Четыре 1-клеточных корабля
        }
        # Отслеживает, сколько кораблей каждого типа уже расставлено каждым игроком
        self.ships_placed_count: Dict[str, Dict[int, int]] = {}
        self.players_placement_complete: Dict[str, bool] = {} # Для отслеживания завершения расстановки в сетевой игре
        self.current_turn_player_name: Optional[str] = None # Для отслеживания, чей сейчас ход в сетевой игре


    def reset_game(self):
        """Сбрасывает состояние игры для новой игры."""
        self.battlefields = {}
        self.current_player_placement_coords = {}
        self.ships_placed_count = {}
        self.players_placement_complete = {}
        self.game_phase = "setup"
        self.current_turn_player_name = None

    def set_game_phase(self, phase: str):
        """Устанавливает текущую фазу игры."""
        self.game_phase = phase

    def add_player(self, player_name: str):
        """Добавляет нового игрока и инициализирует его игровое поле."""
        if player_name not in self.battlefields:
            self.battlefields[player_name] = create_new_game()
            self.current_player_placement_coords[player_name] = []
            # Инициализируем счетчики кораблей для этого игрока
            self.ships_placed_count[player_name] = {length: 0 for length in self.ship_lengths_to_place}
            self.players_placement_complete[player_name] = False

    def set_player_placement_complete(self, player_name: str, complete: bool):
        """Устанавливает статус завершения расстановки для игрока."""
        if player_name in self.players_placement_complete:
            self.players_placement_complete[player_name] = complete

    def are_all_players_placed(self) -> bool:
        """Проверяет, расставили ли все игроки свои корабли."""
        return all(self.players_placement_complete.values())

    def set_current_turn_player_name(self, player_name: str):
        """Устанавливает имя игрока, чей сейчас ход."""
        self.current_turn_player_name = player_name


    def handle_placement_click(self, player_name: str, clicked_coord: Tuple[str, str]) -> Dict[str, Any]:
        """
        Управляет процессом расстановки кораблей для игрока на основе кликов.
        Возвращает словарь с сообщением, статусом успеха и координатами расстановки.
        """
        if player_name not in self.battlefields:
            return {"success": False, "message": "Игрок не найден.", "finished_placement": False}

        battlefield = self.battlefields[player_name]
        current_coords = self.current_player_placement_coords[player_name]
        x, y = clicked_coord

        # Проверяем, является ли клетка уже частью корабля или прилегающей к нему
        cell = battlefield.field[y][x]
        if cell.is_part_of_ship:
             return {"success": False, "message": "Эта клетка уже является частью корабля.", "current_placement_coords": current_coords, "finished_placement": False}
        if not cell.can_place_ship:
             # Если клетка помечена как `can_place_ship=False`, это означает, что она прилегает к уже размещенному кораблю.
             # Эта проверка предотвращает ошибку "Error: Cannot place ship at X Y due to proximity to another ship." во время выбора многоклеточного корабля.
             if len(current_coords) == 0: # Блокируем только если начинаем новый корабль в заблокированной области
                 return {"success": False, "message": "Нельзя начинать новый корабль слишком близко к существующему.", "current_placement_coords": current_coords, "finished_placement": False}


        # Если кликнутая клетка уже есть в текущем выборе, удаляем ее (отключаем)
        if clicked_coord in current_coords:
            current_coords.remove(clicked_coord)
            self.current_player_placement_coords[player_name] = current_coords
            return {"success": True, "message": f"Удалено {x}{y} из текущего выбора.", "current_placement_coords": current_coords, "finished_placement": False}

        # Добавляем кликнутую клетку к текущему выбору
        current_coords.append(clicked_coord)
        self.current_player_placement_coords[player_name] = current_coords

        current_ship_len = len(current_coords)

        # Проверяем, образует ли текущий выбор правильную форму корабля для определенной длины
        # Это клиентская проверка для удобства пользователя, серверная сторона будет перепроверять.
        is_straight = self._is_selection_straight(current_coords)
        is_contiguous = self._is_selection_contiguous(current_coords)

        if not is_straight or not is_contiguous:
            return {"success": False, "message": "Клетки корабля должны быть смежными и находиться на одной прямой.", "current_placement_coords": current_coords, "finished_placement": False}


        # Проверяем, выбрано ли достаточно клеток для любой разрешенной длины корабля
        valid_lengths = [l for l, count in self.ship_lengths_to_place.items() if self.ships_placed_count[player_name][l] < count]
        if current_ship_len in valid_lengths:
            # Пытаемся разместить корабль
            try:
                # Основной метод `add_ship` выполняет свою собственную валидацию, поэтому мы можем просто вызвать его
                place_result = place_ship(battlefield, current_coords)
                if place_result["success"]:
                    self.ships_placed_count[player_name][current_ship_len] += 1
                    message = f"Размещен {current_ship_len}-клеточный корабль. Осталось: {self._get_remaining_ships_message(player_name)}"
                    self.current_player_placement_coords[player_name] = [] # Очищаем выбор для следующего корабля

                    # Проверяем, все ли корабли расставлены
                    all_ships_placed = all(self.ships_placed_count[player_name][length] == count for length, count in self.ship_lengths_to_place.items())
                    return {"success": True, "message": message, "current_placement_coords": [], "finished_placement": all_ships_placed}
                else:
                    # Если размещение не удалось, отменяем текущие координаты
                    current_coords.pop() # Удаляем последнюю добавленную координату
                    self.current_player_placement_coords[player_name] = current_coords
                    return {"success": False, "message": f"Размещение не удалось: {place_result['message']}", "current_placement_coords": current_coords, "finished_placement": False}
            except ValueError as e:
                # Если возникает ValueError во время размещения (например, перекрытие, правила смежности)
                current_coords.pop() # Удаляем последнюю добавленную координату
                self.current_player_placement_coords[player_name] = current_coords
                return {"success": False, "message": f"Ошибка размещения: {e}", "current_placement_coords": current_coords, "finished_placement": False}
        elif current_ship_len > max(self.ship_lengths_to_place.keys()):
            current_coords.pop() # Удаляем последнюю добавленную координату, так как корабль слишком длинный
            self.current_player_placement_coords[player_name] = current_coords
            return {"success": False, "message": "Корабль слишком длинный. Максимальная длина - 4.", "current_placement_coords": current_coords, "finished_placement": False}
        elif current_ship_len not in valid_lengths and current_ship_len <= max(self.ship_lengths_to_place.keys()):
            # Пользователь находится в процессе выбора корабля допустимой длины, но еще не завершил его
            message = f"Выбрано {current_ship_len} клеток. Продолжайте выбирать для получения допустимой длины корабля ({', '.join(map(str, valid_lengths))})."
            return {"success": True, "message": message, "current_placement_coords": current_coords, "finished_placement": False}
        else:
            # Этот случай охватывает выбор длины корабля, которая допустима, но уже достигла максимума
            current_coords.pop()
            self.current_player_placement_coords[player_name] = current_coords
            return {"success": False, "message": f"Вы уже расставили все {current_ship_len}-клеточные корабли.", "current_placement_coords": current_coords, "finished_placement": False}

    def _get_remaining_ships_message(self, player_name: str) -> str:
        """Формирует сообщение о оставшихся кораблях для расстановки."""
        remaining_messages = []
        for length in sorted(self.ship_lengths_to_place.keys(), reverse=True):
            total = self.ship_lengths_to_place[length]
            placed = self.ships_placed_count[player_name][length]
            remaining = total - placed
            if remaining > 0:
                remaining_messages.append(f"{remaining}x{length}")
        if not remaining_messages:
            return "Все корабли расставлены!"
        return f"Осталось расставить: {', '.join(remaining_messages)}"


    def _is_selection_straight(self, coords: List[Tuple[str, str]]) -> bool:
        """Проверяет, находятся ли выбранные клетки на одной прямой (горизонтально или вертикально)."""
        if len(coords) < 2:
            return True # Одна клетка всегда прямая

        x_coords = [c[0] for c in coords]
        y_coords = [c[1] for c in coords]

        is_horizontal = all(y == y_coords[0] for y in y_coords)
        is_vertical = all(x == x_coords[0] for x in x_coords)

        return is_horizontal or is_vertical

    def _is_selection_contiguous(self, coords: List[Tuple[str, str]]) -> bool:
        """Проверяет, являются ли выбранные клетки смежными."""
        if len(coords) < 2:
            return True

        # Преобразуем в числовые координаты для сортировки и сравнения
        num_coords = []
        for x, y in coords:
            x_num = int(x)
            y_idx = list(VERTICAL_KEYS.values()).index(y)
            num_coords.append((x_num, y_idx))

        num_coords.sort() # Сортируем для упрощения проверки смежности

        is_horizontal = all(c[1] == num_coords[0][1] for c in num_coords)
        is_vertical = all(c[0] == num_coords[0][0] for c in num_coords)

        if is_horizontal:
            for i in range(1, len(num_coords)):
                if num_coords[i][0] != num_coords[i-1][0] + 1:
                    return False
        elif is_vertical:
            for i in range(1, len(num_coords)):
                if num_coords[i][1] != num_coords[i-1][1] + 1:
                    return False
        else:
            return False # Не прямая линия

        return True

