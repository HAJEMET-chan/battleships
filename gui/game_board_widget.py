# gui/game_board_widget.py
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QSizePolicy, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QBrush, QPainter

from src.main import VERTICAL_KEYS, HORIZONTAL_KEYS # Предполагается, что они доступны из основной логики игры

class CellButton(QPushButton):
    """
    Пользовательская кнопка QPushButton для одной клетки игрового поля.
    """
    def __init__(self, x: str, y: str):
        super().__init__()
        self.x = x
        self.y = y
        self.setFixedSize(40, 40) # Делаем клетки квадратными
        self.setStyleSheet(self._get_style_sheet("~")) # По умолчанию - пустая вода
        self.setCursor(Qt.PointingHandCursor) # Указываем, что можно кликать
        self.setFlat(True) # Делаем ее похожей на плоскую плитку
        self.state = "~" # Изначальное состояние

    def _get_style_sheet(self, state: str, is_highlighted: bool = False) -> str:
        """
        Возвращает строку стиля CSS для кнопки клетки в зависимости от ее состояния.
        """
        base_style = "border: 1px solid #666; font-weight: bold; color: white;"
        bg_color = "#ADD8E6" # Светло-голубой для воды

        if state == "X":
            bg_color = "#FF4500" # Оранжево-красный для попадания
        elif state == "O":
            bg_color = "#87CEEB" # Небесно-голубой для промаха
        elif state == "S":
            bg_color = "#778899" # Серый для корабля
        elif state == ".":
            bg_color = "#A9A9A9" # Темно-серый для занятой, но не корабельной области (блокировка расстановки)
        elif state == "~":
            bg_color = "#ADD8E6" # Светло-голубой для пустой воды

        if is_highlighted:
            bg_color = "#FFFF00" # Желтый для выделенных клеток во время расстановки

        return f"background-color: {bg_color}; {base_style}"

    def set_state(self, state: str, is_highlighted: bool = False):
        """
        Обновляет визуальное состояние клетки.
        """
        self.state = state
        self.setText(state if state in ["X", "O"] else "") # Показываем X/O только при попадании/промахе
        self.setStyleSheet(self._get_style_sheet(state, is_highlighted))


class GameBoardWidget(QWidget):
    """
    Пользовательский виджет, который отображает одно игровое поле 10x10.
    Излучает сигнал cell_clicked при нажатии на клетку.
    """
    cell_clicked = Signal(str, str) # Излучает координаты (x, y)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(1)
        self.cell_buttons: dict[str, dict[str, CellButton]] = {}
        self.highlighted_cells: list[tuple[str, str]] = []
        self._interactive = True # Контролирует, можно ли кликать по клеткам

        self._init_board_ui()

    def _init_board_ui(self):
        """Инициализирует пользовательский интерфейс доски, добавляя заголовки и кнопки клеток."""
        # Добавляем заголовки столбцов (1-10)
        # Смещение на 1 для меток оси Y
        for i, x_key in enumerate(HORIZONTAL_KEYS.values()):
            label = QLabel(x_key)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #333;")
            self.grid_layout.addWidget(label, 0, i + 1) # Ряд 0, столбцы 1-10

        # Добавляем заголовки строк (А-К) и кнопки клеток
        for i, y_key in enumerate(VERTICAL_KEYS.values()):
            label = QLabel(y_key)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #333;")
            self.grid_layout.addWidget(label, i + 1, 0) # Столбец 0, ряды 1-10

            for j, x_key in enumerate(HORIZONTAL_KEYS.values()):
                cell_button = CellButton(x_key, y_key)
                # Подключаем сигнал нажатия кнопки к обработчику, который излучает cell_clicked
                cell_button.clicked.connect(lambda _, x=x_key, y=y_key: self._on_cell_button_clicked(x, y))
                self.grid_layout.addWidget(cell_button, i + 1, j + 1)
                if y_key not in self.cell_buttons:
                    self.cell_buttons[y_key] = {}
                self.cell_buttons[y_key][x_key] = cell_button

        self.setLayout(self.grid_layout)

    def _on_cell_button_clicked(self, x: str, y: str):
        """Обработчик клика по кнопке клетки."""
        if self._interactive:
            self.cell_clicked.emit(x, y)
        else:
            print(f"Доска неинтерактивна. Невозможно кликнуть {x}{y}.") # Для отладки

    def update_board(self, board_state: list[list[str]]):
        """
        Обновляет визуальное состояние всех клеток на доске.
        board_state - это 2D список строк (например, "X", "O", "S", "~").
        """
        for r_idx, row in enumerate(board_state):
            y_key = VERTICAL_KEYS[r_idx]
            for c_idx, cell_state_char in enumerate(row):
                x_key = HORIZONTAL_KEYS[c_idx]
                if y_key in self.cell_buttons and x_key in self.cell_buttons[y_key]:
                    is_highlighted = (x_key, y_key) in self.highlighted_cells
                    self.cell_buttons[y_key][x_key].set_state(cell_state_char, is_highlighted)

    def highlight_cells(self, coords: list[tuple[str, str]]):
        """
        Выделяет список клеток, обычно для предварительного просмотра расстановки кораблей.
        """
        # Сначала очищаем предыдущие выделения
        for y_key, row_cells in self.cell_buttons.items():
            for x_key, cell_button in row_cells.items():
                if (x_key, y_key) in self.highlighted_cells:
                    # Возвращаем старые выделенные клетки в их обычное состояние
                    cell_button.set_state(cell_button.state, is_highlighted=False)

        self.highlighted_cells = coords
        # Применяем новые выделения
        for x, y in coords:
            if y in self.cell_buttons and x in self.cell_buttons[y]:
                self.cell_buttons[y][x].set_state(self.cell_buttons[y][x].state, is_highlighted=True)

    def set_interactive(self, interactive: bool):
        """
        Устанавливает, являются ли клетки доски кликабельными.
        """
        self._interactive = interactive
        for row_buttons in self.cell_buttons.values():
            for cell_button in row_buttons.values():
                cell_button.setEnabled(interactive)
                cell_button.setCursor(Qt.PointingHandCursor if interactive else Qt.ArrowCursor)

