"""
개별 버튼 위젯
- 이모지/텍스트 아이콘 + 라벨
- label_mode: always(항상) | hover(팝업) | hidden(숨김)
- 우클릭 시그널
- 포커스 가져가지 않음
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QPainterPath, QCursor, QPen


class _HoverPopup(QWidget):
    """호버 시 버튼 이름을 표시하는 플로팅 팝업"""

    def __init__(self, text: str, anchor: QWidget):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        lbl = QLabel(text, self)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("""
            QLabel {
                background: rgba(30, 30, 46, 220);
                color: #cdd6f4;
                font-family: '맑은 고딕', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #585b70;
                border-radius: 6px;
                padding: 5px 10px;
            }
        """)
        lbl.adjustSize()

        self.resize(lbl.size())
        lbl.resize(lbl.size())

        # 버튼 상단 중앙에 위치
        global_pos = anchor.mapToGlobal(QPoint(anchor.width() // 2, 0))
        x = global_pos.x() - self.width() // 2
        y = global_pos.y() - self.height() - 4
        # 화면 밖으로 나가지 않도록 보정
        screen = QApplication.primaryScreen().geometry()
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), y)
        self.move(x, y)


class ButtonWidget(QWidget):
    clicked_action = pyqtSignal(object)   # button_data or None (빈 슬롯)
    right_clicked  = pyqtSignal(object, QPoint)  # button_data, global_pos

    def __init__(self, button_data: dict | None, size: int,
                 label_mode: str, theme: dict, parent=None):
        super().__init__(parent)
        self.button_data = button_data
        self.btn_size    = size
        self.label_mode  = label_mode   # always | hover | hidden
        self.theme       = theme
        self._hovered    = False
        self._popup: _HoverPopup | None = None
        # 이미지 경로 저장 (리사이즈 시 재스케일용)
        self._image_path: str = button_data.get("image_path", "") if button_data else ""

        self.setFixedSize(size, size)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        self._setup_ui()
        self._apply_style()

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _icon_font_size(self, with_label: bool) -> int:
        """이모지 폰트 크기: 설정값 우선, 없으면 버튼 크기 비율"""
        fixed = self.theme.get("icon_font_size", 0)
        if fixed and fixed > 0:
            return fixed
        if with_label:
            return max(18, int(self.btn_size * 0.40))
        else:
            return max(22, int(self.btn_size * 0.52))

    def _label_font_size(self) -> int:
        """이름 텍스트 폰트 크기: 설정값 우선, 없으면 버튼 크기 비율"""
        fixed = self.theme.get("label_font_size", 0)
        if fixed and fixed > 0:
            return fixed
        return max(7, int(self.btn_size * 0.12))

    def _setup_ui(self):
        has_label = (self.label_mode == "always") and bool(self.button_data)
        margin = 3 if has_label else 2

        layout = QVBoxLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── 아이콘 레이블 ──
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        if self.button_data:
            icon       = self.button_data.get("icon", "")
            image_path = self.button_data.get("image_path", "")

            if image_path:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    icon_px = max(24, self.btn_size - 20)
                    self.icon_label.setPixmap(
                        pixmap.scaled(icon_px, icon_px,
                                      Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
                    )
                else:
                    self._set_icon_text(icon or "?", has_label)
            else:
                self._set_icon_text(icon or "?", has_label)
        else:
            # 빈 슬롯 — 폰트 크기는 btn_size 비율 고정 (설정 무관)
            self.icon_label.setText("+")
            pt = max(16, int(self.btn_size * 0.28))
            border = self.theme.get("border_color", "#585b70")
            self.icon_label.setStyleSheet(
                f"font-size: {pt}pt; font-weight: bold; color: {border}; background: transparent;"
            )

        layout.addWidget(self.icon_label)

        # ── 버튼 이름 레이블 (always 모드만) ──
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.name_label.setWordWrap(False)

        if self.button_data:
            self.name_label.setText(self.button_data.get("label", ""))
        else:
            self.name_label.setText("추가")

        lpt = self._label_font_size()
        lcolor = (self.theme.get("text_color", "#cdd6f4") if self.button_data
                  else self.theme.get("border_color", "#585b70"))
        self.name_label.setStyleSheet(
            f"font-size: {lpt}pt; color: {lcolor}; background: transparent;"
        )

        if self.label_mode == "always":
            self.name_label.show()
        else:
            self.name_label.hide()

        layout.addWidget(self.name_label)

    def _set_icon_text(self, text: str, has_label: bool):
        self.icon_label.setText(text)
        pt = self._icon_font_size(has_label)
        color = self.theme.get("text_color", "#cdd6f4")
        self.icon_label.setStyleSheet(
            f"font-size: {pt}pt; color: {color}; background: transparent;"
        )

    def update_size(self, new_size: int):
        """리사이즈 드래그 중 버튼 크기·폰트를 인플레이스로 업데이트."""
        self.btn_size = new_size
        self.setFixedSize(new_size, new_size)
        has_label = (self.label_mode == "always") and bool(self.button_data)
        if self._image_path:
            icon_px = max(24, new_size - 20)
            pm = QPixmap(self._image_path)
            if not pm.isNull():
                self.icon_label.setPixmap(
                    pm.scaled(icon_px, icon_px,
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
                )
        else:
            if self.button_data:
                ipt = self._icon_font_size(has_label)
                icolor = self.theme.get("text_color", "#cdd6f4")
                self.icon_label.setStyleSheet(
                    f"font-size: {ipt}pt; color: {icolor}; background: transparent;"
                )
            else:
                # 빈 슬롯 "+" — btn_size 비율 고정
                ipt = max(16, int(new_size * 0.28))
                border = self.theme.get("border_color", "#585b70")
                self.icon_label.setStyleSheet(
                    f"font-size: {ipt}pt; font-weight: bold; color: {border}; background: transparent;"
                )
        lpt = self._label_font_size()
        lcolor = (self.theme.get("text_color", "#cdd6f4") if self.button_data
                  else self.theme.get("border_color", "#585b70"))
        self.name_label.setStyleSheet(
            f"font-size: {lpt}pt; color: {lcolor}; background: transparent;"
        )
        self.layout().invalidate()
        self.layout().activate()
        self.icon_label.repaint()
        self.name_label.repaint()
        self.repaint()

    # ── 스타일 ────────────────────────────────────────────────────────────────

    def _apply_style(self):
        text   = self.theme.get("text_color",   "#cdd6f4")
        border = self.theme.get("border_color", "#585b70")

        if not self.button_data:
            self.setStyleSheet(f"""
                ButtonWidget {{ background: transparent; border: none; color: {border}; }}
                QLabel {{ background: transparent; color: {border}; }}
            """)
        else:
            bg = self.theme.get("button_color", "#313244")
            self.setStyleSheet(f"""
                ButtonWidget {{ background: {bg}; border: none;
                                border-radius: 8px; color: {text}; }}
                QLabel {{ background: transparent; color: {text}; }}
            """)

    def _set_bg(self, bg: str):
        text   = self.theme.get("text_color",   "#cdd6f4")
        border = self.theme.get("border_color", "#585b70")
        if not self.button_data:
            self.setStyleSheet(f"""
                ButtonWidget {{ background: transparent; border: none; color: {border}; }}
                QLabel {{ background: transparent; color: {border}; }}
            """)
        else:
            self.setStyleSheet(f"""
                ButtonWidget {{ background: {bg}; border: none;
                                border-radius: 8px; color: {text}; }}
                QLabel {{ background: transparent; color: {text}; }}
            """)

    # ── 이벤트 ───────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._set_bg(self.theme.get("button_pressed", "#181825"))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._set_bg(
            self.theme.get("button_hover", "#45475a") if self._hovered
            else self.theme.get("button_color", "#313244")
        )
        if event.button() == Qt.MouseButton.LeftButton:
            if self.rect().contains(event.pos()):
                self.clicked_action.emit(self.button_data)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.button_data, event.globalPosition().toPoint())
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._set_bg(self.theme.get("button_hover", "#45475a"))

        if self.label_mode == "hover" and self.button_data:
            label = self.button_data.get("label", "").strip()
            if label:
                self._popup = _HoverPopup(label, self)
                self._popup.show()

        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._set_bg(self.theme.get("button_color", "#313244"))
        self._close_popup()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self._close_popup()
        super().hideEvent(event)

    def _close_popup(self):
        if self._popup is not None:
            self._popup.close()
            self._popup = None

    # ── 렌더링 ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.button_data:
            color = QColor(
                self.theme.get("button_hover", "#45475a") if self._hovered
                else self.theme.get("button_color", "#313244")
            )
            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
            painter.fillPath(path, color)
        else:
            # 빈 슬롯 점선 테두리
            pen = QPen(QColor(self.theme.get("border_color", "#585b70")))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 7, 7)

        painter.end()
        super().paintEvent(event)
