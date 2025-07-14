# gui/network_setup_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QSpacerItem, QSizePolicy, QMessageBox
from PySide6.QtCore import Qt, Signal

class NetworkSetupDialog(QDialog):
    """
    Диалог для настройки сетевой игры: выбор режима (хост/клиент) и ввод IP.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка сетевой игры")
        self.setModal(True)
        self.setFixedSize(350, 200) # Фиксированный размер для диалога

        self.layout = QVBoxLayout(self)

        # Группа радиокнопок для выбора режима
        self.mode_group = QButtonGroup(self)
        self.host_radio = QRadioButton("Создать игру (Хост)")
        self.join_radio = QRadioButton("Присоединиться к игре (Клиент)")
        self.mode_group.addButton(self.host_radio)
        self.mode_group.addButton(self.join_radio)

        self.host_radio.setChecked(True) # По умолчанию выбран хост

        self.layout.addWidget(self.host_radio)
        self.layout.addWidget(self.join_radio)

        # Поле для ввода IP-адреса (появляется только для клиента)
        self.ip_label = QLabel("IP-адрес хоста:")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Например: 192.168.1.100 или IP Hamachi")
        self.ip_label.hide() # Скрываем по умолчанию
        self.ip_input.hide() # Скрываем по умолчанию

        self.layout.addWidget(self.ip_label)
        self.layout.addWidget(self.ip_input)

        # Соединяем сигналы радиокнопок для управления видимостью поля IP
        self.host_radio.toggled.connect(self._toggle_ip_input)

        self.layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Кнопки OK и Cancel
        self.buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("Начать")
        self.cancel_button = QPushButton("Отмена")

        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.start_button)
        self.buttons_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.buttons_layout)

        self.start_button.clicked.connect(self._on_start_clicked)
        self.cancel_button.clicked.connect(self.reject)

    def _toggle_ip_input(self):
        """Переключает видимость поля ввода IP в зависимости от выбранного режима."""
        is_host = self.host_radio.isChecked()
        self.ip_label.setVisible(not is_host)
        self.ip_input.setVisible(not is_host)

    def _on_start_clicked(self):
        """Обрабатывает нажатие кнопки 'Начать'."""
        if self.join_radio.isChecked() and not self.ip_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите IP-адрес хоста.")
            return
        self.accept()

    def get_network_settings(self) -> tuple[str, str]:
        """
        Возвращает выбранный режим ('host' или 'client') и введенный IP-адрес.
        """
        mode = "host" if self.host_radio.isChecked() else "client"
        ip = self.ip_input.text().strip()
        return mode, ip

