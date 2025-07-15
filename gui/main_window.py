# gui/main_window.py
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Signal, QTimer # Импортируем QTimer для безопасного обновления GUI из потоков
from PySide6.QtGui import QColor, QBrush, QPainter
from typing import Optional, Dict, Any
import sys

from .game_board_widget import GameBoardWidget
from .player_setup_dialog import PlayerSetupDialog
from .network_setup_dialog import NetworkSetupDialog # Новый импорт
from .game_manager import GameManager
from src.api import create_new_game, place_ship, make_shot, get_board_state, is_game_finished, validate_full_battlefield
from src.main import BattleField # Импорт BattleField для подсказок типов
from src.network_manager import NetworkHost, NetworkClient, NetworkManager # Импорт сетевых классов
import threading # Для запуска сетевых операций в отдельном потоке
import sys # Для sys.exit()

class MainWindow(QMainWindow):
    """
    Главное окно приложения "Морской бой".
    Управляет общим макетом, переключением фаз игры и взаимодействием между игровыми полями.
    """
    # Сигналы для безопасного обновления GUI из сетевых потоков
    network_message_received = Signal(dict)
    network_status_updated = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Морской Бой!")
        self.setGeometry(100, 100, 1200, 800) # Увеличенный размер для двух полей

        self.game_manager = GameManager()
        self.current_player_index = 0
        self.players = [] # Будет хранить имена игроков

        self.network_manager: Optional[NetworkManager] = None
        self.network_game_mode: str = "local" # "local", "host", "client"
        self.network_opponent_name: str = "Противник" # Имя сетевого противника

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

        self.reset_button = QPushButton("Начать новую игру (Локально)")
        self.network_game_button = QPushButton("Сетевая игра") # Кнопка для настройки сетевой игры
        self.new_network_game_button = QPushButton("Новая сетевая игра (Без переподключения)") # Новая кнопка
        self.new_network_game_button.setEnabled(False) # Изначально отключена

        self.start_game_button = QPushButton("Начать битву!")
        self.start_game_button.setEnabled(False) # Включить после расстановки всех кораблей

        self.info_layout.addWidget(self.current_player_label)
        self.info_layout.addWidget(self.message_label)
        self.info_layout.addStretch() # Отталкивает содержимое вверх
        self.info_layout.addWidget(self.start_game_button)
        self.info_layout.addWidget(self.reset_button)
        self.info_layout.addWidget(self.network_game_button)
        self.info_layout.addWidget(self.new_network_game_button) # Добавляем новую кнопку

    def _setup_layout(self):
        """Настраивает основной макет окна."""
        self.main_layout.addLayout(self.player1_board_layout)
        self.main_layout.addLayout(self.player2_board_layout)
        self.main_layout.addLayout(self.info_layout)

    def _connect_signals(self):
        """Подключает сигналы виджетов к соответствующим слотам."""
        self.reset_button.clicked.connect(self._initialize_game)
        self.network_game_button.clicked.connect(self._start_network_game_setup) # Подключаем новую кнопку
        self.new_network_game_button.clicked.connect(self._start_new_network_game) # Подключаем новую кнопку
        self.start_game_button.clicked.connect(self._start_game_phase)
        # Подключаем оба виджета поля к одному обработчику кликов
        self.player1_board_widget.cell_clicked.connect(lambda x, y: self._on_board_click(self.player1_board_widget, x, y))
        self.player2_board_widget.cell_clicked.connect(lambda x, y: self._on_board_click(self.player2_board_widget, x, y))

        # Подключаем сигналы для безопасного обновления GUI из сетевых потоков
        self.network_message_received.connect(self._handle_network_message)
        self.network_status_updated.connect(self._handle_network_status_update)

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
        """Инициализирует новую локальную игру, включая запрос имен игроков."""
        self.network_game_mode = "local"
        if self.network_manager:
            self.network_manager.shutdown()
            self.network_manager = None
        self.new_network_game_button.setEnabled(False) # Отключаем кнопку "Новая сетевая игра" для локального режима

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

    def _start_network_game_setup(self):
        """Открывает диалог для настройки сетевой игры."""
        if self.network_manager: # Если уже есть активное сетевое соединение
            self.network_manager.shutdown()
            self.network_manager = None
        self.new_network_game_button.setEnabled(False) # Отключаем, так как это новая настройка

        network_dialog = NetworkSetupDialog(self)
        if network_dialog.exec() == NetworkSetupDialog.Accepted:
            mode, ip = network_dialog.get_network_settings()
            self.network_game_mode = mode
            self.game_manager.reset_game() # Сброс локальной игры

            player_names = []
            if mode == "host":
                player_names = ["Игрок 1 (Хост)", "Игрок 2 (Клиент)"]
                self.network_manager = NetworkHost()
                # Получаем IP-адреса хоста для отображения
                host_ips_str = ", ".join(self.network_manager.host_ips)
                # Включаем порт в сообщение
                self.message_label.setText(f"Хост запущен. Ваши IP-адреса: {host_ips_str}. Порт: {self.network_manager.port}. Ожидание подключения...")
                # Запускаем хост в отдельном потоке, чтобы не блокировать GUI
                threading.Thread(target=self.network_manager.start_host, daemon=True).start()
            else: # client
                player_names = ["Игрок 2 (Клиент)", "Игрок 1 (Хост)"] # Для клиента, его имя - Игрок 2
                self.network_manager = NetworkClient(ip)
                self.message_label.setText(f"Попытка подключения к хосту {ip}:{self.network_manager.port}...")
                # Запускаем клиент в отдельном потоке
                threading.Thread(target=self.network_manager.connect_to_host, daemon=True).start()

            self.players = player_names
            for name in self.players:
                self.game_manager.add_player(name)

            # Устанавливаем коллбэки для сетевого менеджера
            self.network_manager.set_callbacks(
                message_cb=lambda msg: self.network_message_received.emit(msg),
                status_cb=lambda status, msg: self.network_status_updated.emit(status, msg)
            )

            self.current_player_index = 0 # Локальный игрок всегда Игрок 1 в своем представлении
            self._update_current_player_display()
            self.start_game_button.setEnabled(False) # В сетевой игре кнопка "Начать битву" будет активирована по сети
            self.new_network_game_button.setEnabled(False) # Отключаем до подключения

            self.game_manager.set_game_phase("network_setup")
            self._update_board_displays() # Обновляем, чтобы показать пустые поля

        else:
            QMessageBox.information(self, "Сетевая игра отменена", "Настройка сетевой игры была отменена. Возврат к локальной игре.")
            self._initialize_game() # Возвращаемся к локальной игре

    def _start_new_network_game(self):
        """
        Начинает новую сетевую игру, не отключая существующее сетевое соединение.
        """
        if not self.network_manager or not self.network_manager.is_connected:
            QMessageBox.warning(self, "Ошибка", "Нет активного сетевого соединения для начала новой сетевой игры.")
            self.new_network_game_button.setEnabled(False)
            return

        # Сброс состояния игры, но сохранение сетевого менеджера
        self.game_manager.reset_game()
        # Повторно добавляем игроков, чтобы инициализировать их поля и счетчики кораблей
        for name in self.players:
            self.game_manager.add_player(name)

        self.current_player_index = 0 # Локальный игрок всегда Игрок 1 в своем представлении
        self._update_current_player_display()

        self.message_label.setText(f"{self.players[self.current_player_index]}, расставьте свои корабли! ({self.game_manager._get_remaining_ships_message(self.players[self.current_player_index])})")
        self.start_game_button.setEnabled(False) # Отключить до расстановки
        self.new_network_game_button.setEnabled(False) # Отключить до расстановки и готовности

        self.game_manager.set_game_phase("placement")
        self._update_board_displays() # Обновляем, чтобы показать поля для расстановки

        # Отправляем сообщение противнику, что мы начинаем новую игру
        if self.network_manager.is_connected:
            self.network_manager.send_game_data("new_game_request", {
                "player_name": self.players[self.current_player_index] # Отправляем свое имя
            })
            self.message_label.setText("Запрошена новая сетевая игра. Ожидание ответа противника...")
            # Блокируем расстановку до подтверждения от противника
            self.player1_board_widget.set_interactive(False)


    def _handle_network_status_update(self, is_connected: bool, message: str):
        """Обрабатывает обновления статуса сетевого соединения."""
        self.message_label.setText(f"Сетевой статус: {message}")
        if is_connected:
            QMessageBox.information(self, "Соединение установлено", message)
            # После установки соединения, переходим к фазе расстановки кораблей
            self.game_manager.set_game_phase("placement")
            self.message_label.setText(f"{self.players[self.current_player_index]}, расставьте свои корабли! ({self.game_manager._get_remaining_ships_message(self.players[self.current_player_index])})")
            self._update_board_displays()
            self.new_network_game_button.setEnabled(True) # Включаем кнопку "Новая сетевая игра"
        elif not is_connected and self.game_manager.game_phase != "network_setup":
            QMessageBox.critical(self, "Ошибка сети", f"Соединение потеряно: {message}. Игра будет перезапущена локально.")
            self._initialize_game() # Перезапускаем локальную игру при потере соединения

    def _handle_network_message(self, message: Dict[str, Any]):
        """Обрабатывает входящие сетевые сообщения."""
        msg_type = message.get("type")
        payload = message.get("payload")

        if msg_type == "ship_placement":
            # Противник расставил корабль. Обновляем его поле (для нашего представления).
            # В сетевой игре каждый игрок расставляет на своем поле, а потом отправляет подтверждение.
            # Здесь мы просто получаем сигнал, что противник закончил расстановку.
            # Фактическое состояние поля противника будет обновляться только при выстрелах.
            opponent_name = self.players[self._get_opponent_index()]
            self.game_manager.ships_placed_count[opponent_name] = payload["ships_placed_count"]
            if payload["finished_placement"]:
                self.game_manager.set_player_placement_complete(opponent_name, True)
                self.message_label.setText(f"{opponent_name} закончил расстановку кораблей.")
                self._check_all_players_placed()

        elif msg_type == "shot":
            # Получен выстрел от противника
            local_player_name = self.players[self.current_player_index] # Это наше поле, по которому стреляли
            opponent_player_name = self.players[self._get_opponent_index()]

            # Когда мы получаем сообщение "shot", это означает, что противник только что выстрелил.
            # Следовательно, сейчас должен быть ход противника.
            # Если по какой-то причине current_turn_player_name указывает на нашего локального игрока,
            # это означает рассинхронизацию.
            if self.game_manager.current_turn_player_name == local_player_name:
                QMessageBox.warning(self, "Ошибка хода", "Получен выстрел в ваш ход, но это ход противника! Синхронизация нарушена.")
                return

            x, y = payload["x"], payload["y"]
            battlefield_to_hit = self.game_manager.battlefields[local_player_name] # Противник стреляет по нашему полю

            shot_result = make_shot(battlefield_to_hit, x, y)
            self.message_label.setText(f"Противник выстрелил по {x}{y}. Результат: {shot_result['message']}")
            self._update_board_displays()

            # Отправляем результат выстрела обратно противнику
            self.network_manager.send_game_data("shot_result", {
                "x": x,
                "y": y,
                "cell_state": shot_result["cell_state"],
                "ship_sunk_id": shot_result["ship_sunk_id"],
                "game_over": shot_result["game_over"],
                "message": shot_result["message"] # Включаем сообщение для удобства
            })

            if shot_result["game_over"]:
                QMessageBox.information(self, "Игра окончена!", f"Все ваши корабли потоплены! {opponent_player_name} побеждает!")
                self.message_label.setText(f"Игра окончена! {opponent_player_name} побеждает!")
                self.game_manager.set_game_phase("game_over")
                self.player1_board_widget.set_interactive(False)
                self.player2_board_widget.set_interactive(False)
            elif shot_result["cell_state"] == "hit" or shot_result["cell_state"] == "killed":
                # Если противник попал, его ход продолжается. Мы просто ждем следующего выстрела.
                self.message_label.setText(f"Противник попал! Ждем следующего выстрела от {opponent_player_name}.")
            else: # Промах
                # Если противник промахнулся, ход переходит к нам
                self.message_label.setText(f"Противник промахнулся! Ваш ход, {local_player_name}.")
                self._switch_turn_network() # Переключаем ход на локального игрока

        elif msg_type == "shot_result":
            # Получен результат нашего выстрела от противника
            x, y = payload["x"], payload["y"]
            cell_state = payload["cell_state"]
            ship_sunk_id = payload["ship_sunk_id"]
            game_over = payload["game_over"]
            message = payload.get("message", cell_state) # Получаем сообщение

            # Обновляем наше представление поля противника на основе полученного результата
            # Здесь мы можем обновить состояние соответствующей клетки на поле player2_board_widget
            # (которое отображает поле противника)
            opponent_battlefield = self.game_manager.battlefields[self.players[self._get_opponent_index()]]
            # Имитируем hit/miss для обновления состояния клетки на нашем локальном представлении
            # (хотя фактический hit произошел на поле противника)
            cell = opponent_battlefield.field[y][x]
            if cell_state == "hit" or cell_state == "killed":
                cell.is_hit = True
                cell.is_part_of_ship = True # Помечаем как часть корабля, чтобы отобразить "X"
                if cell_state == "killed":
                    # Если корабль потоплен, можно пометить все его части как killed
                    # Для этого нужно будет найти все клетки этого корабля на нашем поле противника
                    # и пометить их как killed. Это сложнее, пока просто отобразим "X".
                    pass
            elif cell_state == "miss":
                cell.is_miss = True

            self._update_board_displays()
            self.message_label.setText(f"Ваш выстрел по {x}{y}: {message}")


            if game_over:
                QMessageBox.information(self, "Игра окончена!", f"Поздравляем, {self.players[self.current_player_index]}! Вы потопили все корабли противника!")
                self.message_label.setText(f"Игра окончена! {self.players[self.current_player_index]} побеждает!")
                self.game_manager.set_game_phase("game_over")
                self.player1_board_widget.set_interactive(False)
                self.player2_board_widget.set_interactive(False)
            elif cell_state == "hit" or cell_state == "killed":
                # Если мы попали, наш ход продолжается
                self.message_label.setText(f"{self.players[self.current_player_index]}, вы попали! Стреляйте снова!")
            else: # Промах
                self.message_label.setText(f"{self.players[self.current_player_index]}, вы промахнулись! Ход переходит к противнику.")
                self._switch_turn_network() # Переключаем ход на противника

        elif msg_type == "game_start":
            # Получено сообщение о начале игры от хоста
            if self.network_game_mode == "client":
                self.message_label.setText("Хост начал игру! Приготовьтесь к битве.")
                self.game_manager.set_game_phase("in_progress")
                
                # Определяем, кто начинает, на основе индекса хоста
                # Если хост говорит, что игрок с индексом 0 (игрок хоста) начинает,
                # то для клиента это означает, что начинает противник (players[1]).
                # Если хост говорит, что игрок с индексом 1 (игрок клиента) начинает,
                # то для клиента это означает, что начинает локальный игрок (players[0]).
                # Текущая логика хоста всегда отправляет 0, означая, что хост начинает.
                if payload["starting_player_index"] == 0: # Игрок хоста начинает
                    self.game_manager.set_current_turn_player_name(self.players[1]) # Для клиента это противник
                else: # Игрок клиента начинает (если хост когда-либо отправит это)
                    self.game_manager.set_current_turn_player_name(self.players[0]) # Для клиента это локальный игрок

                self._update_current_player_display()
                self._update_board_displays() # Обновит интерактивность на основе current_turn_player_name

                # Обновляем сообщение в зависимости от того, кто на самом деле начинает
                if self.game_manager.current_turn_player_name == self.players[0]: # Если наш ход
                    self.message_label.setText(f"Ваш ход, {self.players[0]}! Выстрелите по полю противника.")
                else: # Если ход противника
                    self.message_label.setText(f"Ход противника. Ожидаем выстрела от {self.players[1]}.")

        elif msg_type == "new_game_request":
            # Получен запрос на новую игру от противника
            if self.network_game_mode != "local":
                reply = QMessageBox.question(self, "Новая игра",
                                             f"Игрок {payload.get('player_name', 'противник')} предлагает начать новую сетевую игру. Начать?",
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.game_manager.reset_game()
                    # Повторно добавляем игроков, чтобы инициализировать их поля и счетчики кораблей
                    for name in self.players:
                        self.game_manager.add_player(name)

                    self.current_player_index = 0 # Локальный игрок всегда Игрок 1 в своем представлении
                    self._update_current_player_display()
                    self.message_label.setText(f"{self.players[self.current_player_index]}, расставьте свои корабли! ({self.game_manager._get_remaining_ships_message(self.players[self.current_player_index])})")
                    self.start_game_button.setEnabled(False)
                    self.new_network_game_button.setEnabled(False) # Отключить до расстановки и готовности
                    self.game_manager.set_game_phase("placement")
                    self._update_board_displays()
                    self.network_manager.send_game_data("new_game_response", {"accepted": True})
                    self.player1_board_widget.set_interactive(True) # Разблокируем для расстановки
                else:
                    self.network_manager.send_game_data("new_game_response", {"accepted": False})
                    self.message_label.setText("Запрос на новую игру отклонен.")
                    self.new_network_game_button.setEnabled(True) # Если отклонили, можно снова запросить

        elif msg_type == "new_game_response":
            # Получен ответ на наш запрос новой игры
            if payload["accepted"]:
                QMessageBox.information(self, "Новая игра", "Противник принял запрос на новую игру. Приступайте к расстановке!")
                self.message_label.setText(f"{self.players[self.current_player_index]}, расставьте свои корабли! ({self.game_manager._get_remaining_ships_message(self.players[self.current_player_index])})")
                self.player1_board_widget.set_interactive(True) # Разблокируем для расстановки
                self.new_network_game_button.setEnabled(False) # Отключить до расстановки и готовности
            else:
                QMessageBox.warning(self, "Новая игра", "Противник отклонил запрос на новую игру.")
                self.message_label.setText("Противник отклонил запрос на новую игру. Продолжайте текущую или начните новую локальную.")
                self.new_network_game_button.setEnabled(True) # Если отклонили, можно снова запросить


    def _update_current_player_display(self):
        """Обновляет метку с именем текущего игрока."""
        # В сетевой игре current_player_index всегда 0 для локального игрока,
        # а _get_opponent_index() - 1.
        # Сообщение о ходе будет более явным.
        if self.network_game_mode == "local":
            self.current_player_label.setText(f"Текущий игрок: {self.players[self.current_player_index]}")
        else:
            # В сетевой игре "Вы играете за:" всегда отображает имя локального игрока
            self.current_player_label.setText(f"Вы играете за: {self.players[0]}")


    def _update_board_displays(self):
        """
        Обновляет визуальное представление обоих игровых полей
        в зависимости от текущей фазы игры и активного игрока.
        """
        player1_name = self.players[0]
        player2_name = self.players[1] # Это всегда противник в сетевой игре

        if self.game_manager.game_phase == "placement":
            # В локальной игре:
            if self.network_game_mode == "local":
                if self.current_player_index == 0: # Игрок 1 расставляет корабли
                    self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=True))
                    self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=False)) # Поле противника скрыто
                    self.player1_label.setText(f"{player1_name}'s Board (Ваши корабли)")
                    self.player2_label.setText(f"{player2_name}'s Board (Скрыто)")
                    self.player1_board_widget.set_interactive(True)
                    self.player2_board_widget.set_interactive(False)
                    self.player1_board_widget.highlight_cells(self.game_manager.current_player_placement_coords[player1_name])
                    self.player2_board_widget.highlight_cells([])
                else: # Игрок 2 расставляет корабли
                    self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=False)) # Поле противника скрыто
                    self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=True))
                    self.player1_label.setText(f"{player1_name}'s Board (Скрыто)")
                    self.player2_label.setText(f"{player2_name}'s Board (Ваши корабли)")
                    self.player1_board_widget.set_interactive(False)
                    self.player2_board_widget.set_interactive(True)
                    self.player2_board_widget.highlight_cells(self.game_manager.current_player_placement_coords[player2_name])
                    self.player1_board_widget.highlight_cells([])
            # В сетевой игре (фаза расстановки):
            else: # network_game_mode is "host" or "client"
                # Всегда показываем собственное поле слева, поле противника справа
                self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=True))
                self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=False)) # Поле противника всегда скрыто

                self.player1_label.setText(f"{player1_name}'s Board (Ваши корабли)")
                self.player2_label.setText(f"{player2_name}'s Board (Скрыто)")

                # Интерактивность для расстановки в сетевой игре
                # Она будет управляться _handle_network_message для new_game_response
                # Изначально интерактивно, пока не отправится запрос на новую игру
                self.player1_board_widget.set_interactive(True)
                self.player2_board_widget.set_interactive(False)

                self.player1_board_widget.highlight_cells(self.game_manager.current_player_placement_coords[player1_name])
                self.player2_board_widget.highlight_cells([])

        elif self.game_manager.game_phase == "in_progress":
            # В фазе игры, текущий игрок видит свое поле (корабли видны) и поле противника (корабли скрыты).
            # Интерактивным полем всегда является поле противника.
            # В сетевой игре: player1_board_widget - всегда наше поле, player2_board_widget - всегда поле противника
            self.player1_board_widget.update_board(get_board_state(self.game_manager.battlefields[player1_name], show_ships=True))
            self.player2_board_widget.update_board(get_board_state(self.game_manager.battlefields[player2_name], show_ships=False))
            self.player1_label.setText(f"{player1_name}'s Board (Ваши корабли)")
            self.player2_label.setText(f"{player2_name}'s Board (Воды противника)")

            # Интерактивность в сетевой игре зависит от того, чей сейчас ход (локальный или удаленный)
            if self.game_manager.current_turn_player_name == player1_name: # Если наш ход
                self.player1_board_widget.set_interactive(False) # Свое поле не для стрельбы
                self.player2_board_widget.set_interactive(True)  # Поле противника для стрельбы
            else: # Ход противника
                self.player1_board_widget.set_interactive(False)
                self.player2_board_widget.set_interactive(False)
                # Сообщение о ходе противника уже установлено в _handle_network_message или _switch_turn_network
                # self.message_label.setText(f"Ход противника. Ожидаем выстрела от {self.players[self._get_opponent_index()]}.")

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

        elif self.game_manager.game_phase == "network_setup":
            # В фазе сетевой настройки поля неинтерактивны и пустые
            self.player1_board_widget.update_board(get_board_state(create_new_game(), show_ships=False))
            self.player2_board_widget.update_board(get_board_state(create_new_game(), show_ships=False))
            self.player1_label.setText(f"{player1_name}'s Board")
            self.player2_label.setText(f"{player2_name}'s Board")
            self.player1_board_widget.set_interactive(False)
            self.player2_board_widget.set_interactive(False)
            self.player1_board_widget.highlight_cells([])
            self.player2_board_widget.highlight_cells([])


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

            # В сетевой игре отправляем сообщение о завершении расстановки
            if self.network_game_mode != "local" and self.network_manager and self.network_manager.is_connected:
                self.network_manager.send_game_data("ship_placement", {
                    "player_name": current_player_name,
                    "finished_placement": True,
                    "ships_placed_count": self.game_manager.ships_placed_count[current_player_name]
                })
                self.game_manager.set_player_placement_complete(current_player_name, True)
                self.message_label.setText(f"Вы закончили расстановку. Ожидаем, пока {self.players[self._get_opponent_index()]} закончит.")
                self._check_all_players_placed() # Проверяем, готовы ли оба игрока
            else: # Локальная игра
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

    def _check_all_players_placed(self):
        """Проверяет, расставили ли оба игрока корабли в сетевой игре."""
        if self.network_game_mode != "local" and self.game_manager.are_all_players_placed():
            self.start_game_button.setEnabled(True) # В сетевой игре это кнопка для хоста
            self.message_label.setText("Оба игрока расставили корабли. Нажмите 'Начать битву!' (только хост).")
            self.game_manager.set_game_phase("pre_game_ready")
            self.player1_board_widget.set_interactive(False)
            self.player2_board_widget.set_interactive(False)
            # Хост может начать игру
            if self.network_game_mode == "host":
                self.start_game_button.setEnabled(True)
            else:
                self.start_game_button.setEnabled(False) # Клиент ждет команды от хоста


    def _start_game_phase(self):
        """
        Переводит игру в фазу сражения после расстановки кораблей.
        Включает валидацию полей.
        """
        local_player_name = self.players[0]
        opponent_player_name = self.players[1]

        # Валидируем только поле локального игрока
        local_player_bf = self.game_manager.battlefields[local_player_name]
        validation_local = validate_full_battlefield(local_player_bf)

        if not validation_local["is_valid"]:
            QMessageBox.critical(self, "Ошибка валидации", f"Поле {local_player_name} недействительно: {validation_local['message']}")
            return

        if self.network_game_mode == "local":
            # В локальной игре валидируем поле второго игрока тоже
            opponent_bf_local = self.game_manager.battlefields[opponent_player_name]
            validation_opponent_local = validate_full_battlefield(opponent_bf_local)
            if not validation_opponent_local["is_valid"]:
                QMessageBox.critical(self, "Ошибка валидации", f"Поле {opponent_player_name} недействительно: {validation_opponent_local['message']}")
                return

            self.current_player_index = 0 # Игрок 1 начинает первым
            self.game_manager.set_current_turn_player_name(self.players[self.current_player_index]) # Устанавливаем текущий ход
            self._update_current_player_display()
            self.message_label.setText(f"{self.players[self.current_player_index]}, ваш ход! Выстрелите по полю {self.players[self._get_opponent_index()]}.")
        else: # Сетевая игра (хост или клиент)
            # В сетевой игре, если мы хост, мы должны убедиться, что клиент тоже готов
            if self.network_game_mode == "host":
                if not self.game_manager.players_placement_complete[opponent_player_name]:
                    QMessageBox.warning(self, "Ожидание игрока", f"{opponent_player_name} еще не закончил расстановку кораблей. Пожалуйста, подождите.")
                    return
                
                starting_player_name = local_player_name # Хост (локальный игрок) начинает
                self.game_manager.set_current_turn_player_name(starting_player_name)
                # Отправляем сообщение клиенту о начале игры и кто начинает
                self.network_manager.send_game_data("game_start", {"starting_player_index": 0}) # 0 - это всегда локальный игрок
                self.message_label.setText(f"Вы начинаете! Ваш ход, {local_player_name}! Выстрелите по полю противника.")
            else: # Если мы клиент, мы не должны нажимать "Начать битву!"
                QMessageBox.warning(self, "Ошибка", "Только хост может начать битву.")
                return


        self.game_manager.set_game_phase("in_progress")
        self.start_game_button.setEnabled(False) # Отключаем кнопку "Начать битву" после старта

        # Устанавливаем интерактивность полей для фазы стрельбы
        self._update_board_displays() # Обновляем, чтобы установить правильную интерактивность

    def _handle_shot(self, x: str, y: str):
        """
        Обрабатывает клики по полю для совершения выстрелов.
        """
        # В сетевой игре, если сейчас не наш ход, игнорируем клик
        if self.network_game_mode != "local" and self.game_manager.current_turn_player_name != self.players[self.current_player_index]:
            self.message_label.setText("Сейчас не ваш ход. Ожидайте выстрела противника.")
            return

        current_player_name = self.players[self.current_player_index]
        opponent_player_name = self.players[self._get_opponent_index()]
        opponent_battlefield = self.game_manager.battlefields[opponent_player_name]

        if self.network_game_mode == "local":
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
                    self._switch_turn_local()
            else:
                self.message_label.setText(f"Неверный выстрел: {shot_result['message']}")
        else: # Сетевая игра
            if self.network_manager and self.network_manager.is_connected:
                # Отправляем выстрел противнику
                self.network_manager.send_game_data("shot", {"x": x, "y": y})
                self.message_label.setText(f"Выстрел по {x}{y} отправлен. Ожидаем ответа противника...")
                self.player2_board_widget.set_interactive(False) # Блокируем поле пока ждем ответа
            else:
                self.message_label.setText("Нет активного сетевого соединения.")


    def _switch_turn_local(self):
        """Переключает ход между игроками в локальной игре."""
        self.current_player_index = 1 - self.current_player_index # Переключаемся между 0 и 1
        self.game_manager.set_current_turn_player_name(self.players[self.current_player_index]) # Обновляем текущий ход в менеджере
        self._update_current_player_display()
        # Обновляем доски, чтобы отразить вид нового игрока и интерактивность
        self._update_board_displays()

        QMessageBox.information(self, "Смена хода", f"Теперь ход {self.players[self.current_player_index]}. Отвернитесь, {self.players[self._get_opponent_index()]}!")
        self.message_label.setText(f"{self.players[self.current_player_index]}, ваш ход! Выстрелите по полю {self.players[self._get_opponent_index()]}.")

    def _switch_turn_network(self):
        """Переключает ход в сетевой игре."""
        # В сетевой игре current_player_index всегда 0 (локальный игрок)
        # Мы просто меняем, чей ход в game_manager
        current_turn_player = self.game_manager.current_turn_player_name
        if current_turn_player == self.players[0]: # Если был наш ход (локальный игрок)
            self.game_manager.set_current_turn_player_name(self.players[1]) # Ход противника
            self.message_label.setText(f"Ход противника. Ожидаем выстрела от {self.players[self._get_opponent_index()]}.")
            self.player2_board_widget.set_interactive(False) # Блокируем поле противника для стрельбы
        else: # Если был ход противника
            self.game_manager.set_current_turn_player_name(self.players[0]) # Наш ход (локальный игрок)
            self.message_label.setText(f"Ваш ход, {self.players[self.current_player_index]}! Выстрелите по полю противника.")
            self.player2_board_widget.set_interactive(True) # Разблокируем поле противника для выстрела

        self._update_current_player_display()
        self._update_board_displays()


    def _get_opponent_index(self) -> int:
        """Возвращает индекс противника текущего игрока."""
        # В локальной игре это просто 1 - current_player_index
        # В сетевой игре, если current_player_index - это мы (0), то противник - 1.
        # Если current_player_index - это противник (1), то мы - 0.
        return 1 - self.current_player_index

    def closeEvent(self, event):
        """Обработчик события закрытия окна."""
        if self.network_manager:
            self.network_manager.shutdown() # Корректно закрываем сетевое соединение
        super().closeEvent(event)

