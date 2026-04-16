"""
설정 화면
- 테마 색상, 투명도, 그리드 배열, 라벨 표시, 자동시작, 내보내기/불러오기
"""

import sys
import tempfile as _tf
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSlider, QComboBox, QCheckBox,
    QColorDialog, QGroupBox, QDialogButtonBox, QFileDialog,
    QScrollArea, QWidget, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap



class ColorButton(QPushButton):
    """색상 선택 버튼 — 현재 색상을 배경으로 표시, 텍스트는 밝기 기반 자동 전환"""

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(90, 28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._refresh()
        self.clicked.connect(self._pick)

    def _text_color(self) -> str:
        """배경색이 어두우면 흰 글씨, 밝으면 검은 글씨"""
        c = QColor(self._color)
        # 상대 휘도 계산 (간단 근사)
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        return "#ffffff" if lum < 128 else "#000000"

    def _refresh(self):
        fg = self._text_color()
        self.setStyleSheet(
            f"background: {self._color}; color: {fg}; "
            f"border: 1px solid #999; border-radius: 4px; "
            f"font-size: 11px; font-weight: bold;"
        )
        self.setText(self._color)

    def _pick(self):
        col = QColorDialog.getColor(QColor(self._color), self, "색상 선택")
        if col.isValid():
            self._color = col.name()
            self._refresh()

    @property
    def color(self):
        return self._color


# ── 로고 로드 헬퍼 ───────────────────────────────────────────────────────────

def _load_logo(filename: str) -> "QPixmap | None":
    """원본 QPixmap 반환. 파일이 없으면 None."""
    import os, sys
    base = (sys._MEIPASS
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, filename)
    pm = QPixmap(path)
    return None if pm.isNull() else pm


class AboutDialog(QDialog):
    STYLE = """
        QDialog, QWidget {
            background: #f5f5f5;
            font-family: '맑은 고딕', 'Segoe UI', sans-serif;
            color: #1a1a1a;
        }
        QLabel { background: transparent; color: #1a1a1a; border: none; }
        QPushButton {
            background: #ffffff; color: #1a1a1a;
            border: 1px solid #b0b0b0; border-radius: 4px;
            padding: 4px 16px; min-height: 26px;
        }
        QPushButton:hover { background: #e8f0fe; border-color: #0078d4; color: #0078d4; }
        QPushButton:pressed { background: #cce0ff; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("만든이")
        self.setFixedWidth(320)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setStyleSheet(self.STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(28, 28, 28, 24)

        # ─ 행 1: 논산여상 로고 + "장동욱 with ClaudeCode" ─
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        logo1_label = QLabel()
        logo1_label.setFixedSize(56, 56)
        logo1_label.setScaledContents(True)
        logo1_label.setStyleSheet("background: transparent; border: none;")
        pm1 = _load_logo("논산여상 로고.png")
        if pm1:
            logo1_label.setPixmap(pm1)
        row1.addWidget(logo1_label)

        name_label = QLabel("장동욱  with  ClaudeCode")
        name_label.setStyleSheet("font-size: 13px; font-weight: bold; background: transparent;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(name_label)
        row1.addStretch()
        layout.addLayout(row1)

        # ─ 행 2: 갓쌤에듀 로고 (중앙, 가로 폭 우선) ─
        # 원본 비율 1024:255 ≈ 4:1 → 표시 크기 220×55
        logo2_label = QLabel()
        logo2_label.setFixedSize(220, 55)
        logo2_label.setScaledContents(True)
        logo2_label.setStyleSheet("background: transparent; border: none;")
        pm2 = _load_logo("갓쌤에듀 로고.png")
        if pm2:
            logo2_label.setPixmap(pm2)
        logo2_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo2_wrap = QHBoxLayout()
        logo2_wrap.addStretch()
        logo2_wrap.addWidget(logo2_label)
        logo2_wrap.addStretch()
        layout.addLayout(logo2_wrap)

        # ─ 행 3: 날짜 및 제품명 (중앙) ─
        date_label = QLabel("2026.4.16.  알잘딱버튼")
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_label.setStyleSheet("font-size: 11px; color: #666666;")
        layout.addWidget(date_label)

        # ─ 닫기 버튼 ─
        close_btn = QPushButton("닫기")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


# ── SVG 아이콘 경로 ──────────────────────────────────────────────────────────
_COMBO_ARROW_PATH = ""
_SPIN_UP_PATH = ""
_SPIN_DOWN_PATH = ""
_CHECK_PATH = ""
try:
    _td = _tf.gettempdir()

    _p = _td + "/vr_combo_arrow.svg"
    with open(_p, "wb") as _f:
        _f.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 6">'
                 b'<polygon points="0,0 10,0 5,6" fill="#555555"/></svg>')
    _COMBO_ARROW_PATH = _p.replace("\\", "/")

    _p = _td + "/vr_spin_up.svg"
    with open(_p, "wb") as _f:
        _f.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 6">'
                 b'<polygon points="5,0 10,6 0,6" fill="#555555"/></svg>')
    _SPIN_UP_PATH = _p.replace("\\", "/")

    _p = _td + "/vr_spin_down.svg"
    with open(_p, "wb") as _f:
        _f.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 6">'
                 b'<polygon points="0,0 10,0 5,6" fill="#555555"/></svg>')
    _SPIN_DOWN_PATH = _p.replace("\\", "/")

    _p = _td + "/vr_check.svg"
    with open(_p, "wb") as _f:
        _f.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
                 b'<polyline points="2,8 6,12 14,4" fill="none" stroke="#ffffff"'
                 b' stroke-width="2.5" stroke-linecap="round"'
                 b' stroke-linejoin="round"/></svg>')
    _CHECK_PATH = _p.replace("\\", "/")
except Exception:
    pass


class SettingsDialog(QDialog):

    # 설정 창 전용 스타일 (Dock 스타일 상속 차단)
    STYLE = """
        QDialog, QWidget, QScrollArea, QScrollArea > QWidget > QWidget {
            background: #f5f5f5;
            color: #1a1a1a;
            font-family: '맑은 고딕', 'Segoe UI', sans-serif;
            font-size: 12px;
        }
        QGroupBox {
            background: #ffffff;
            color: #1a1a1a;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            margin-top: 10px;
            padding: 8px 6px 6px 6px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 4px;
            color: #333333;
        }
        QLabel {
            background: transparent;
            color: #1a1a1a;
        }
        QComboBox {
            background: #ffffff;
            color: #1a1a1a;
            border: 1px solid #b0b0b0;
            border-radius: 4px;
            padding: 3px 8px;
            min-height: 24px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 22px;
            border-left: 1px solid #c0c0c0;
            border-radius: 0 4px 4px 0;
            background: #ebebeb;
        }
        QComboBox::down-arrow {
            image: url(__ARROW__);
            width: 10px;
            height: 6px;
        }
        QComboBox QAbstractItemView {
            background: #ffffff;
            color: #1a1a1a;
            selection-background-color: #0078d4;
            selection-color: #ffffff;
        }
        QSpinBox {
            background: #ffffff;
            color: #1a1a1a;
            border: 1px solid #b0b0b0;
            border-radius: 4px;
            padding: 3px 6px;
            min-height: 24px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            width: 18px;
            border: none;
            background: #e8e8e8;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background: #d0d8f0;
        }
        QSpinBox::up-arrow {
            image: url(__SPIN_UP__);
            width: 8px;
            height: 5px;
        }
        QSpinBox::down-arrow {
            image: url(__SPIN_DOWN__);
            width: 8px;
            height: 5px;
        }
        QSlider::groove:horizontal {
            height: 4px;
            background: #d0d0d0;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #0078d4;
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        QSlider::sub-page:horizontal {
            background: #0078d4;
            border-radius: 2px;
        }
        QCheckBox {
            color: #1a1a1a;
            spacing: 6px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #b0b0b0;
            border-radius: 3px;
            background: #ffffff;
        }
        QCheckBox::indicator:checked {
            background: #0078d4;
            border-color: #0078d4;
            image: url(__CHECK__);
        }
        QPushButton {
            background: #ffffff;
            color: #1a1a1a;
            border: 1px solid #b0b0b0;
            border-radius: 4px;
            padding: 4px 12px;
            min-height: 26px;
        }
        QPushButton:hover {
            background: #e8f0fe;
            border-color: #0078d4;
            color: #0078d4;
        }
        QPushButton:pressed { background: #cce0ff; }
        QDialogButtonBox QPushButton[text="OK"],
        QDialogButtonBox QPushButton[text="확인"] {
            background: #0078d4;
            color: #ffffff;
            border-color: #005a9e;
            font-weight: bold;
        }
        QDialogButtonBox QPushButton[text="OK"]:hover,
        QDialogButtonBox QPushButton[text="확인"]:hover {
            background: #006cbd;
        }
        QScrollBar:vertical {
            background: #f0f0f0;
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #c0c0c0;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setWindowTitle("알잘딱버튼 설정")
        self.setMinimumWidth(460)
        self.setMinimumHeight(500)
        self.setStyleSheet(
            self.STYLE
            .replace("__ARROW__", _COMBO_ARROW_PATH)
            .replace("__SPIN_UP__", _SPIN_UP_PATH)
            .replace("__SPIN_DOWN__", _SPIN_DOWN_PATH)
            .replace("__CHECK__", _CHECK_PATH)
        )

        self._setup_ui()
        self._load()

    def _setup_ui(self):
        outer = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        inner_widget = QWidget()
        layout = QVBoxLayout(inner_widget)
        layout.setSpacing(12)
        scroll.setWidget(inner_widget)
        outer.addWidget(scroll)

        # ─ 테마 ─────────────────────────────────────────────────────────────
        theme_group = QGroupBox("테마 색상")
        theme_layout = QFormLayout(theme_group)
        theme = self.config.get("theme", {})

        self.color_btns = {}
        THEME_LABELS = {
            "background":    "배경",
            "button_color":  "버튼 기본",
            "button_hover":  "버튼 호버",
            "button_pressed":"버튼 클릭",
            "text_color":    "텍스트",
            "accent_color":  "강조",
            "border_color":  "테두리",
        }
        for key, label in THEME_LABELS.items():
            btn = ColorButton(theme.get(key, "#888888"))
            self.color_btns[key] = btn
            theme_layout.addRow(label + ":", btn)
        layout.addWidget(theme_group)

        # ─ 투명도 ────────────────────────────────────────────────────────────
        opacity_group = QGroupBox("투명도")
        opacity_layout = QHBoxLayout(opacity_group)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.opacity_val_label = QLabel("92%")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_val_label.setText(f"{v}%"))
        opacity_layout.addWidget(QLabel("30%"))
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(QLabel("100%"))
        opacity_layout.addWidget(self.opacity_val_label)
        layout.addWidget(opacity_group)

        # ─ 그리드 배열 ────────────────────────────────────────────────────────
        grid_group = QGroupBox("버튼 배열")
        grid_layout = QHBoxLayout(grid_group)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setFixedWidth(60)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 10)
        self.rows_spin.setFixedWidth(60)
        grid_layout.addWidget(QLabel("가로(열):"))
        grid_layout.addWidget(self.cols_spin)
        grid_layout.addWidget(QLabel("  세로(행):"))
        grid_layout.addWidget(self.rows_spin)
        grid_layout.addStretch()
        layout.addWidget(grid_group)

        # ─ 라벨 표시 ─────────────────────────────────────────────────────────
        label_group = QGroupBox("버튼 이름 표시")
        label_layout = QHBoxLayout(label_group)
        self.label_combo = QComboBox()
        self.label_combo.addItem("항상 표시", "always")
        self.label_combo.addItem("호버 시 툴팁", "hover")
        self.label_combo.addItem("숨김", "hidden")
        label_layout.addWidget(QLabel("이름 표시 방식:"))
        label_layout.addWidget(self.label_combo)
        label_layout.addStretch()
        layout.addWidget(label_group)

        # ─ 폰트 크기 ──────────────────────────────────────────────────────────
        font_group = QGroupBox("버튼 폰트 크기")
        font_layout = QHBoxLayout(font_group)
        self.icon_font_spin = QSpinBox()
        self.icon_font_spin.setRange(8, 72)
        self.icon_font_spin.setSuffix(" pt")
        self.icon_font_spin.setFixedWidth(72)
        self.label_font_spin = QSpinBox()
        self.label_font_spin.setRange(6, 28)
        self.label_font_spin.setSuffix(" pt")
        self.label_font_spin.setFixedWidth(72)
        font_layout.addWidget(QLabel("이모지:"))
        font_layout.addWidget(self.icon_font_spin)
        font_layout.addSpacing(16)
        font_layout.addWidget(QLabel("이름 텍스트:"))
        font_layout.addWidget(self.label_font_spin)
        font_layout.addStretch()
        layout.addWidget(font_group)

        # ─ 자동 시작 ─────────────────────────────────────────────────────────
        misc_group = QGroupBox("기타")
        misc_layout = QVBoxLayout(misc_group)
        self.autostart_check = QCheckBox("Windows 시작 시 자동 실행")
        self.autohide_check = QCheckBox("화면 가장자리에서 자동 숨김")
        misc_layout.addWidget(self.autostart_check)
        misc_layout.addWidget(self.autohide_check)
        layout.addWidget(misc_group)

        # ─ 내보내기 / 불러오기 ────────────────────────────────────────────────
        io_group = QGroupBox("설정 내보내기 / 불러오기")
        io_layout = QHBoxLayout(io_group)
        export_btn = QPushButton("📤 내보내기")
        import_btn = QPushButton("📥 불러오기")
        export_btn.clicked.connect(self._export)
        import_btn.clicked.connect(self._import)
        io_layout.addWidget(export_btn)
        io_layout.addWidget(import_btn)
        io_layout.addStretch()
        layout.addWidget(io_group)

        # ─ 만든이 ───────────────────────────────────────────────────────────
        about_group = QGroupBox("만든이")
        about_layout = QHBoxLayout(about_group)
        about_btn = QPushButton("ℹ 만든이 정보")
        about_btn.clicked.connect(self._open_about)
        about_layout.addWidget(about_btn)
        about_layout.addStretch()
        layout.addWidget(about_group)

        layout.addStretch()

        # ─ OK / Cancel ─
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _load(self):
        # 투명도
        opacity = int(self.config.get("opacity", 0.92) * 100)
        self.opacity_slider.setValue(opacity)

        # 그리드
        self.cols_spin.setValue(self.config.get("grid.cols", 3))
        self.rows_spin.setValue(self.config.get("grid.rows", 2))

        # 라벨 모드
        label_mode = self.config.get("label_mode", "always")
        idx = self.label_combo.findData(label_mode)
        if idx >= 0:
            self.label_combo.setCurrentIndex(idx)

        # 폰트 크기
        self.icon_font_spin.setValue(self.config.get("icon_font_size", 28))
        self.label_font_spin.setValue(self.config.get("label_font_size", 9))

        # 자동시작
        self.autostart_check.setChecked(self.config.get("autostart", False))

        # 자동숨김
        self.autohide_check.setChecked(self.config.get("autohide", True))

    def _save_and_accept(self):
        # 테마
        theme = {k: btn.color for k, btn in self.color_btns.items()}
        self.config.set("theme", theme)

        # 투명도
        self.config.set("opacity", self.opacity_slider.value() / 100)

        # 그리드
        self.config.set("grid.cols", self.cols_spin.value())
        self.config.set("grid.rows", self.rows_spin.value())

        # 라벨
        self.config.set("label_mode", self.label_combo.currentData())

        # 폰트 크기
        self.config.set("icon_font_size", self.icon_font_spin.value())
        self.config.set("label_font_size", self.label_font_spin.value())

        # 자동시작
        autostart = self.autostart_check.isChecked()
        self.config.set("autostart", autostart)
        if autostart:
            self._set_autostart(True)

        # 자동숨김
        self.config.set("autohide", self.autohide_check.isChecked())

        self.config.save_config()
        self.accept()

    def _open_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "설정 내보내기", "알잘딱버튼_설정백업.json",
            "JSON 파일 (*.json)")
        if path:
            ok = self.config.export_config(path)
            if ok:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "완료", "설정을 내보냈습니다.")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "실패", "내보내기 실패.")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "설정 불러오기", "", "JSON 파일 (*.json)")
        if path:
            ok = self.config.import_config(path)
            if ok:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "완료",
                    "설정을 불러왔습니다.\n창을 재시작하면 적용됩니다.")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "실패", "불러오기 실패.")

    def _set_autostart(self, enable: bool):
        """Windows 레지스트리 자동시작 등록/해제"""
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "알잘딱버튼"
            import os
            exe_path = os.path.abspath(sys.argv[0])

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path,
                                0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print(f"[settings] 자동시작 설정 실패: {e}")
