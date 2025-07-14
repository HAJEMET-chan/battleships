# gui/player_setup_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox

class PlayerSetupDialog(QDialog):
    """
    Диалог для ввода имен игроков в начале игры.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка игроков")
        self.setModal(True) # Делаем его блокирующим диалогом

        self.layout = QVBoxLayout(self)

        self.player1_label = QLabel("Имя Игрока 1:")
        self.player1_input = QLineEdit()
        self.player1_input.setPlaceholderText("Введите имя Игрока 1")
        self.layout.addWidget(self.player1_label)
        self.layout.addWidget(self.player1_input)

        self.player2_label = QLabel("Имя Игрока 2:")
        self.player2_input = QLineEdit()
        self.player2_input.setPlaceholderText("Введите имя Игрока 2")
        self.layout.addWidget(self.player2_label)
        self.layout.addWidget(self.player2_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        # Устанавливаем имена по умолчанию для быстрого тестирования
        self.player1_input.setText("Игрок Один")
        self.player2_input.setText("Игрок Два")


    def get_player_names(self) -> list[str]:
        """
        Возвращает список введенных имен игроков.
        """
        return [self.player1_input.text().strip(), self.player2_input.text().strip()]

