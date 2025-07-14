# gui/app.py
import sys
from PySide6.QtWidgets import QApplication
from .main_window import MainWindow

def run_gui():
    """
    Запускает графический интерфейс игры.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


