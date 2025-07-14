# gui/main_window.py
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal
import sys

from .game_board_widget import GameBoardWidget
from .player_setup_dialog import PlayerSetupDialog
from .game_manager import GameManager
from src.api import create_new_game, place_ship, make_shot, get_board_state, is_game_finished, validate_full_battlefield
from src.main import BattleField # Импорт BattleField для подсказок типов

class MainWindow(QMainWindow):
    """
    Главное окно приложения "Морской бой".
    Управляет общим макетом, переключением фаз игры и взаимодействием между игровыми полями.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Морской Бой!")
        self.setGeometry(100, 100, 1200, 800) # Увеличенный размер для двух полей

        self.game_manager = GameManager()
        self.current_player_index = 0
        self.players = [] # Будет хранить имена игроков

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._initialize_game()

    def _create_widgets(self):
        """Создает все виджеты, используемые в главном окне."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Поле Игрока 1 (Собственное поле)
        self.player1_board_layout = QVBoxLayout()
        self.player1_label = QLabel("Поле Игрока 1 (Ваши корабли)")
        self.player1_label.setAlignment(Qt.AlignCenter)
        self.player1_board_widget = GameBoardWidget()
        self.player1_board_layout.addWidget(self.player1_label)
        self.player1_board_layout.addWidget(self.player1_board_widget)

        # Поле Игрока 2 (Поле противника / Целевое поле)
        self.player2_board_layout = QVBoxLayout()
        self.player2_label = QLabel("Поле Игрока 2 (Воды противника)")
        self.player2_label.setAlignment(Qt.AlignCenter)
        self.player2_board_widget = GameBoardWidget()
        self.player2_board_layout.addWidget(self.player2_label)
        self.player2_board_layout.addWidget(self.player2_board_widget)

        # Информация об игре и элементы управления
        self.info_layout = QVBoxLayout()
        self.current_player_label = QLabel("Текущий игрок: ")
        self.current_player_label.setStyleSheet("font-weight: bold; font-size: 18px;")
        self.message_label = QLabel("Добро пожаловать в Морской бой! Расставьте свои корабли.")
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-size: 14px; color: #333;")

        self.reset_button = QPushButton("Начать новую игру")
        self.start_game_button = QPushButton("Начать битву!")
        self.start_game_button.setEnabled(False) # Включить после расстановки всех кораблей

        self.info_layout.addWidget(self.current_player_label)
        self.info_layout.addWidget(self.message_label)
        self.info_layout.addStretch() # Отталкивает содержимое вверх
        self.info_layout.addWidget(self.start_game_button)
        self.info_layout.addWidget(self.reset_button)

    def _setup_layout(self):
        """Настраивает основной макет окна."""
        self.main_layout.addLayout(self.player1_board_layout)
        self.main_layout.addLayout(self.player2_board_layout)
        self.main_layout.addLayout(self.info_layout)

    def _connect_signals(self):
        """Подключает сигналы виджетов к соответствующим слотам."""
        self.reset_button.clicked.connect(self._initialize_game)
        self.start_game_button.clicked.connect(self._start_game_phase)
        # Подключаем оба виджета поля к одному обработчику кликов
        self.player1_board_widget.cell_clicked.connect(lambda x, y: self._on_board_click(self.player1_board_widget, x, y))
        self.player2_board_widget.cell_clicked.connect(lambda x, y: self._on_board_click(self.player2_board_widget, x, y))

    def _on_board_click(self, clicked_board_widget: GameBoardWidget, x: str, y: str):
        """
        Единый обработчик для кликов по любому игровому полю.
        Маршрутизирует клик либо на расстановку кораблей, либо на выстрел.
        """
        if self.game_manager.game_phase == "placement":
            # Во время расстановки кораблей, текущий игрок кликает по СВОЕМУ полю.
            # player1_board_widget всегда отображает поле текущего игрока для расстановки.
            if self.current_player_index == 0 and clicked_board_widget == self.player1_board_widget:
                self._handle_ship_placement(x, y)
            elif self.current_player_index == 1 and clicked_board_widget == self.player2_board_widget:
                self._handle_ship_placement(x, y)
            else:
                self.message_label.setText("Пожалуйста, расставляйте корабли на своем поле.")
        elif self.game_manager.game_phase == "in_progress":
            # Во время игры, текущий игрок кликает по полю ПРОТИВНИКА.
            # Если current_player_index == 0, он кликает по player2_board_widget (правое поле).
            # Если current_player_index == 1, он кликает по player1_board_widget (левое поле).
            if self.current_player_index == 0 and clicked_board_widget == self.player2_board_widget:
                self._handle_shot(x, y)
            elif self.current_player_index == 1 and clicked_board_widget == self.player1_board_widget:
                self._handle_shot(x, y)
            else:
                self.message_label.setText("Пожалуйста, стреляйте по полю противника.")
        else:
            self.message_label.setText("Игра не в активной фазе (расстановка или стрельба).")


    def _initialize_game(self):
        """Инициализирует новую игру, включая запрос имен игроков."""
        self.game_manager.reset_game()
        self.players = []

        setup_dialog = PlayerSetupDialog(self)
        if setup_dialog.exec() == PlayerSetupDialog.Accepted:
            self.players = setup_dialog.get_player_names()
            if len(self.players) < 2 or not all(self.players): # Проверяем, что оба имени введены
                QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите имена для обоих игроков.")
                self._initialize_game() # Перезапускаем настройку
                return
        else:
            QMessageBox.information(self, "Игра отменена", "Настройка игроков была отменена.")
            sys.exit() # Выходим, если настройка отменена

        # Добавляем игроков в менеджер игры
        for player_name in self.players:
            self.game_manager.add_player(player_name)

        # Устанавливаем текущего игрока (Игрок 1 начинает расстановку)
        self.current_player_index = 0
        self._update_current_player_display()

        self.message_label.setText(f"{self.players[self.current_player_index]}, расставьте свои корабли! ({self.game_manager._get_remaining_ships_message(self.players[self.current_player_index])})")
        self.start_game_button.setEnabled(False)
        self.game_manager.set_game_phase("placement")

        # Устанавливаем начальные состояния полей и интерактивность для расстановки Игрока 1
        self._update_board_displays() # Это теперь правильно установит интерактивность для Игрока 1

    def _update_current_player_display(self):
        """Обновляет метку с именем текущего игрока."""
        self.current_player_label.setText(f"Текущий игрок: {self.players[self.current_player_index]}")

    def _update_board_displays(self):
        """
        Обновляет визуальное представление обоих игровых полей
        в зависимости от текущей фазы игры и активного игрока.
        """
        player1_name = self.players[0]
        player2_name = self.players[1]

        if self.game_manager.game_phase == "placement":
            if self.current_player_index == 0: # Игрок 1 расставляет корабли
                self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=True))
                self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=False)) # Поле противника скрыто
                self.player1_label.setText(f"{player1_name}'s Board (Ваши корабли)")
                self.player2_label.setText(f"{player2_name}'s Board (Скрыто)")
                self.player1_board_widget.set_interactive(True)
                self.player2_board_widget.set_interactive(False)
                # Выделяем клетки на активном поле текущего игрока
                self.player1_board_widget.highlight_cells(self.game_manager.current_player_placement_coords[player1_name])
                self.player2_board_widget.highlight_cells([]) # Убеждаемся, что другое поле не выделено
            else: # Игрок 2 расставляет корабли
                self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=False)) # Поле противника скрыто
                self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=True))
                self.player1_label.setText(f"{player1_name}'s Board (Скрыто)")
                self.player2_label.setText(f"{player2_name}'s Board (Ваши корабли)")
                self.player1_board_widget.set_interactive(False)
                self.player2_board_widget.set_interactive(True)
                # Выделяем клетки на активном поле текущего игрока
                self.player2_board_widget.highlight_cells(self.game_manager.current_player_placement_coords[player2_name])
                self.player1_board_widget.highlight_cells([]) # Убеждаемся, что другое поле не выделено

        elif self.game_manager.game_phase == "in_progress":
            # В фазе игры, текущий игрок видит свое поле (корабли видны) и поле противника (корабли скрыты).
            # Интерактивным полем всегда является поле противника.
            if self.current_player_index == 0: # Ход Игрока 1
                self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=True))
                self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=False))
                self.player1_label.setText(f"{player1_name}'s Board (Ваши корабли)")
                self.player2_label.setText(f"{player2_name}'s Board (Воды противника)")
                self.player1_board_widget.set_interactive(False) # Свое поле не для стрельбы
                self.player2_board_widget.set_interactive(True)  # Поле противника для стрельбы

            else: # Ход Игрока 2
                self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=False)) # Поле противника для стрельбы
                self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=True))
                self.player1_label.setText(f"{player1_name}'s Board (Воды противника)")
                self.player2_label.setText(f"{player2_name}'s Board (Ваши корабли)")
                self.player1_board_widget.set_interactive(True)  # Поле противника для стрельбы
                self.player2_board_widget.set_interactive(False) # Свое поле не для стрельбы

            self.player1_board_widget.highlight_cells([]) # Очищаем выделения от расстановки
            self.player2_board_widget.highlight_cells([]) # Очищаем выделения от расстановки

        elif self.game_manager.game_phase == "pre_game_ready" or self.game_manager.game_phase == "game_over":
            # В этих фазах оба поля неинтерактивны
            self.player1_board_widget.set_interactive(False)
            self.player2_board_widget.set_interactive(False)
            self.player1_board_widget.highlight_cells([])
            self.player2_board_widget.highlight_cells([])
            # Отображаем поля с кораблями для обоих игроков, чтобы можно было видеть расстановку после игры
            self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=True))
            self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=True))
            self.player1_label.setText(f"{player1_name}'s Board (Ваши корабли)")
            self.player2_label.setText(f"{player2_name}'s Board (Ваши корабли)") # Для просмотра после игры

        # Убеждаемся, что обновления распространяются
        self.player1_board_widget.update()
        self.player2_board_widget.update()


    def _handle_ship_placement(self, x: str, y: str):
        """
        Обрабатывает клики по полю для расстановки кораблей.
        """
        current_player_name = self.players[self.current_player_index]
        battlefield = self.game_manager.battlefields[current_player_name]

        # Используем менеджер игры для обработки логики расстановки
        result = self.game_manager.handle_placement_click(current_player_name, (x, y))
        self.message_label.setText(result["message"])

        # Обновляем выделение на основе текущих выбранных клеток
        # Важно: выделение всегда происходит на активном поле текущего игрока
        if self.current_player_index == 0:
            self.player1_board_widget.highlight_cells(result.get("current_placement_coords", []))
        else: # self.current_player_index == 1
            self.player2_board_widget.highlight_cells(result.get("current_placement_coords", []))

        self._update_board_displays() # Обновляем состояние поля

        if result["finished_placement"]:
            QMessageBox.information(self, "Расстановка завершена", f"Расстановка кораблей для {current_player_name} завершена!")
            # Переключаем игрока или начинаем игру
            if self.current_player_index == 0:
                self.current_player_index = 1
                self._update_current_player_display()
                # Обновляем доски, чтобы показать пустое поле следующего игрока для расстановки
                self._update_board_displays()
                self.message_label.setText(f"{self.players[self.current_player_index]}, расставьте свои корабли! ({self.game_manager._get_remaining_ships_message(self.players[self.current_player_index])})")
            else:
                # Оба игрока расставили корабли
                self.start_game_button.setEnabled(True)
                self.message_label.setText("Все корабли расставлены! Нажмите 'Начать битву!', чтобы начать сражение.")
                self.game_manager.set_game_phase("pre_game_ready")
                self.player1_board_widget.set_interactive(False)
                self.player2_board_widget.set_interactive(False)


    def _start_game_phase(self):
        """
        Переводит игру в фазу сражения после расстановки кораблей.
        Включает валидацию полей.
        """
        # Валидируем оба поля перед началом игры
        player1_bf = self.game_manager.battlefields[self.players[0]]
        player2_bf = self.game_manager.battlefields[self.players[1]]

        validation1 = validate_full_battlefield(player1_bf)
        validation2 = validate_full_battlefield(player2_bf)

        if not validation1["is_valid"]:
            QMessageBox.critical(self, "Ошибка валидации", f"Поле {self.players[0]} недействительно: {validation1['message']}")
            return
        if not validation2["is_valid"]:
            QMessageBox.critical(self, "Ошибка валидации", f"Поле {self.players[1]} недействительно: {validation2['message']}")
            return

        self.game_manager.set_game_phase("in_progress")
        self.start_game_button.setEnabled(False)
        self.current_player_index = 0 # Игрок 1 начинает первым
        self._update_current_player_display()
        self.message_label.setText(f"{self.players[self.current_player_index]}, ваш ход! Выстрелите по полю {self.players[self._get_opponent_index()]}.")

        # Устанавливаем интерактивность полей для фазы стрельбы
        self._update_board_displays() # Обновляем, чтобы установить правильную интерактивность

    def _handle_shot(self, x: str, y: str):
        """
        Обрабатывает клики по полю для совершения выстрелов.
        """
        current_player_name = self.players[self.current_player_index]
        opponent_player_name = self.players[self._get_opponent_index()]
        opponent_battlefield = self.game_manager.battlefields[opponent_player_name]

        shot_result = make_shot(opponent_battlefield, x, y)
        self.message_label.setText(shot_result["message"])

        if shot_result["success"]:
            self._update_board_displays() # Обновляем оба поля, чтобы отразить выстрел

            if shot_result["game_over"]:
                QMessageBox.information(self, "Игра окончена!", f"Поздравляем, {current_player_name}! Вы потопили все корабли {opponent_player_name}!")
                self.message_label.setText(f"Игра окончена! {current_player_name} побеждает!")
                self.game_manager.set_game_phase("game_over")
                self.player1_board_widget.set_interactive(False)
                self.player2_board_widget.set_interactive(False)
            elif shot_result["cell_state"] == "hit" or shot_result["cell_state"] == "killed":
                # Текущий игрок получает еще один ход, если попал или потопил
                self.message_label.setText(f"{current_player_name}, вы попали! Стреляйте снова!")
            else: # Промах
                self.message_label.setText(f"{current_player_name}, вы промахнулись! Ход переходит к {opponent_player_name}.")
                self._switch_turn()
        else:
            self.message_label.setText(f"Неверный выстрел: {shot_result['message']}")


    def _switch_turn(self):
        """Переключает ход между игроками."""
        self.current_player_index = 1 - self.current_player_index # Переключаемся между 0 и 1
        self._update_current_player_display()
        # Обновляем доски, чтобы отразить вид нового игрока и интерактивность
        self._update_board_displays()

        QMessageBox.information(self, "Смена хода", f"Теперь ход {self.players[self.current_player_index]}. Отвернитесь, {self.players[self._get_opponent_index()]}!")
        self.message_label.setText(f"{self.players[self.current_player_index]}, ваш ход! Выстрелите по полю {self.players[self._get_opponent_index()]}.")


    def _get_opponent_index(self) -> int:
        """Возвращает индекс противника текущего игрока."""
        return 1 - self.current_player_index

