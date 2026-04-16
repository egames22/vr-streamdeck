"""
폴더형 버튼 클릭 시 나타나는 팝업 창
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QCursor

from button_widget import ButtonWidget


class FolderPopup(QWidget):
    button_clicked = pyqtSignal(dict)
    closed = pyqtSignal()

    def __init__(self, sub_buttons: list, theme: dict,
                 button_size: int, label_mode: str, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.sub_buttons = sub_buttons
        self.theme = theme
        self.button_size = button_size
        self.label_mode = label_mode

        self._setup_ui()

        # 외부 클릭 감지 타이머
        self._close_timer = QTimer()
        self._close_timer.setInterval(100)
        self._close_timer.timeout.connect(self._check_outside_click)
        self._close_timer.start()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        for btn_data in self.sub_buttons:
            btn = ButtonWidget(btn_data, self.button_size,
                               self.label_mode, self.theme)
            btn.clicked_action.connect(self._on_sub_button_clicked)
            layout.addWidget(btn)

        self.adjustSize()

    def _on_sub_button_clicked(self, data):
        if data:
            self.button_clicked.emit(data)
        self.close()

    def _check_outside_click(self):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QCursor
        cursor = QCursor.pos()
        if not self.geometry().contains(cursor):
            if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
                self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(self.theme.get("background", "#1e1e2e"))
        bg.setAlpha(230)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        painter.fillPath(path, bg)
        painter.end()
        super().paintEvent(event)

    def closeEvent(self, event):
        self._close_timer.stop()
        self.closed.emit()
        super().closeEvent(event)
