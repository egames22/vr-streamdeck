"""
메인 Dock 창
- 프레임 없음, 항상 위, 포커스 빼앗지 않음
- 드래그 이동, 가장자리 흡착, 자동 숨김, 핀 고정
- 버튼 그리드 + 페이지 시스템
"""

import uuid
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QApplication, QMenu, QSystemTrayIcon, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QCursor, QIcon, QPixmap, QFont, QPen

from button_widget import ButtonWidget
from folder_popup import FolderPopup
from edit_dialog import EditDialog
from settings_dialog import SettingsDialog
from actions import run_action, paste_for_hotkey, _log as _action_log
from hotkey_manager import HotkeyManager, HotkeyEventFilter, _log as _hk_log


SNAP_DISTANCE = 30      # 가장자리 흡착 감지 거리 (px)
HIDE_STRIP = 4          # 숨김 상태 노출 두께 (px)
AUTOHIDE_INTERVAL = 120 # ms
RESIZE_GRIP = 10        # 리사이즈 핸들 두께 (px)
MIN_BTN_SIZE = 40       # 버튼 최소 크기 (px)
# 독 레이아웃 고정 여백 (좌6+우6=12, 상4+하4=8, 상단바28, 하단바26, 스페이싱3×2=6)
_H_FIXED = 12           # 좌우 마진
_V_FIXED = 8 + 28 + 26 + 6  # 상하마진 + 상단바 + 하단바 + 스페이싱


class DockWindow(QWidget):

    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.current_page = 0
        self._drag_pos = None
        self._snapped = self.config.get("snapped", None)
        self._hidden = False
        self._folder_popup = None

        # 리사이즈 상태
        self._resize_edge: str | None = None
        self._resize_start_pos = None
        self._resize_start_size = None
        self._resize_start_x: int = 0   # 왼쪽 리사이즈용 초기 x 좌표
        self._last_resize_edge: str = ""  # 완료 후 스냅 방향 결정용
        self._resize_timer = None   # _setup_resize_timer() 에서 초기화

        self._hotkey_manager = HotkeyManager()
        self._hotkey_filter  = HotkeyEventFilter(self._hotkey_manager)
        QApplication.instance().installNativeEventFilter(self._hotkey_filter)
        self._registered_hotkeys: set = set()   # 등록된 shortcut 문자열 집합
        # shortcut → {page_index: button_data}  (페이지별 디스패치 테이블)
        self._hotkey_table: dict[str, dict[int, dict]] = {}
        self._last_hotkey_fp: frozenset = frozenset()  # 핫키 지문 (중복 sync 방지)

        self._setup_window()
        self._setup_ui()
        self._apply_theme()
        self._restore_position()
        self._setup_autohide()
        self._setup_resize_timer()
        self._setup_tray()
        self._refresh_buttons()

    # ── 창 설정 ──────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def showEvent(self, event):
        """WS_EX_NOACTIVATE: 버튼 클릭 시에도 절대 포커스를 빼앗지 않음"""
        super().showEvent(event)
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                                 style | WS_EX_NOACTIVATE)
        except Exception:
            pass

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(6, 4, 6, 4)
        self._main_layout.setSpacing(3)

        self._main_layout.addWidget(self._make_top_bar())

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(4)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.addWidget(self._grid_widget)

        self._main_layout.addWidget(self._make_bottom_bar())

    def _make_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(28)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)

        self._top_bar = bar
        self._top_bar_layout = layout

        self._title = QLabel("≡ 알잘딱버튼")
        self._title.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self._title)
        layout.addStretch()

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setToolTip("항상 표시 (핀)")
        self._pin_btn.setFixedSize(26, 22)
        self._pin_btn.setCheckable(True)
        self._pin_btn.setChecked(self.config.get("pinned", False))
        self._pin_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._pin_btn.clicked.connect(self._toggle_pin)
        layout.addWidget(self._pin_btn)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setToolTip("설정")
        self._settings_btn.setFixedSize(26, 22)
        self._settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        self._minimize_btn = QPushButton("─")
        self._minimize_btn.setToolTip("최소화")
        self._minimize_btn.setFixedSize(26, 22)
        self._minimize_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._minimize_btn.setObjectName("minimize_btn")
        self._minimize_btn.clicked.connect(self._do_minimize)
        layout.addWidget(self._minimize_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setToolTip("닫기")
        self._close_btn.setFixedSize(26, 22)
        self._close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._close_btn.setObjectName("close_btn")
        self._close_btn.clicked.connect(QApplication.quit)
        layout.addWidget(self._close_btn)

        return bar

    def _make_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(26)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedSize(22, 20)
        self._prev_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._prev_btn.clicked.connect(self._prev_page)
        layout.addWidget(self._prev_btn)

        self._page_label = QLabel("1 / 1")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self._page_label)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedSize(22, 20)
        self._next_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._next_btn.clicked.connect(self._next_page)
        layout.addWidget(self._next_btn)

        layout.addStretch()

        add_page_btn = QPushButton("+ 페이지")
        add_page_btn.setFixedHeight(20)
        add_page_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        add_page_btn.clicked.connect(self._add_page)
        layout.addWidget(add_page_btn)

        del_page_btn = QPushButton("- 페이지")
        del_page_btn.setFixedHeight(20)
        del_page_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        del_page_btn.setObjectName("del_page_btn")
        del_page_btn.clicked.connect(self._del_page)
        layout.addWidget(del_page_btn)

        return bar

    # ── 탑바 컴팩트 모드 ──────────────────────────────────────────────────────

    def _update_top_bar_for_cols(self, cols: int):
        """cols==1 일 때 탑바를 최소화해 그리드 너비에 맞춤."""
        compact = (cols == 1)
        self._title.setVisible(not compact)
        btn_w, btn_h = (20, 18) if compact else (26, 22)
        for btn in (self._pin_btn, self._settings_btn, self._minimize_btn, self._close_btn):
            btn.setFixedSize(btn_w, btn_h)
        self._top_bar_layout.setSpacing(2 if compact else 4)
        self._top_bar.setFixedHeight(22 if compact else 28)

    # ── 버튼 그리드 갱신 ──────────────────────────────────────────────────────

    def _refresh_buttons(self, auto_size: bool = True):
        self.setUpdatesEnabled(False)
        # 그리드 비우기
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = self.config.get("grid.cols", 3)
        self._update_top_bar_for_cols(cols)
        rows = self.config.get("grid.rows", 2)
        btn_size = self.config.get("button_size", 64)
        label_mode = self.config.get("label_mode", "always")
        theme = dict(self.config.get("theme", {}))
        theme["icon_font_size"] = self.config.get("icon_font_size", 28)
        theme["label_font_size"] = self.config.get("label_font_size", 9)

        pages = self.config.pages
        if not pages:
            return

        if self.current_page >= len(pages):
            self.current_page = max(0, len(pages) - 1)

        page_buttons = pages[self.current_page].get("buttons", [])

        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                data = page_buttons[idx] if idx < len(page_buttons) else None

                btn = ButtonWidget(data, btn_size, label_mode, theme)
                btn.clicked_action.connect(self._on_button_click)
                btn.right_clicked.connect(
                    lambda d, pos, row=r, col=c: self._on_right_click(d, pos, row, col)
                )
                self._grid_layout.addWidget(btn, r, c)

        total = len(pages)
        self._page_label.setText(f"{self.current_page + 1} / {total}")
        self._prev_btn.setEnabled(self.current_page > 0)
        self._next_btn.setEnabled(self.current_page < total - 1)

        if auto_size:
            self.adjustSize()
        self.setUpdatesEnabled(True)
        self._sync_hotkeys()

    # ── 버튼 클릭 처리 ────────────────────────────────────────────────────────

    def _on_button_click(self, button_data):
        if button_data is None:
            # 빈 슬롯 → 편집 다이얼로그
            self._add_button_from_empty()
            return

        action_type = button_data.get("action_type")
        if action_type == "folder_button":
            self._toggle_folder_popup(button_data)
        elif action_type == "emoji_insert":
            self._open_emoji_insert_picker()
        else:
            run_action(button_data)

    def _open_emoji_insert_picker(self):
        """이모지 삽입: 포커스 창 저장 → 이모지 선택 → 복원 후 붙여넣기"""
        import ctypes
        import threading
        import time

        # 현재 포커스 창 저장
        try:
            prev_hwnd = ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            prev_hwnd = None

        from edit_dialog import EmojiPickerDialog
        from PyQt6.QtWidgets import QApplication as _App
        dlg = EmojiPickerDialog(self)
        dlg.adjustSize()

        # 화면 중앙에 팝업 배치
        screen = _App.primaryScreen().availableGeometry()
        dlg.move(
            screen.center().x() - dlg.width() // 2,
            screen.center().y() - dlg.height() // 2,
        )

        if not dlg.exec() or not dlg.selected:
            return

        emoji = dlg.selected

        def _paste():
            time.sleep(0.05)
            # 이전 창에 포커스 복원
            if prev_hwnd:
                try:
                    ctypes.windll.user32.SetForegroundWindow(prev_hwnd)
                    time.sleep(0.08)
                except Exception:
                    pass
            # 클립보드에 이모지 저장 후 붙여넣기
            from actions import paste_for_hotkey
            paste_for_hotkey(emoji, "clipboard")

        threading.Thread(target=_paste, daemon=True).start()

    def _toggle_folder_popup(self, button_data):
        if self._folder_popup and self._folder_popup.isVisible():
            self._folder_popup.close()
            return

        theme = dict(self.config.get("theme", {}))
        theme["icon_font_size"] = self.config.get("icon_font_size", 28)
        theme["label_font_size"] = self.config.get("label_font_size", 9)
        btn_size = self.config.get("button_size", 64)
        label_mode = self.config.get("label_mode", "always")
        sub_buttons = button_data.get("sub_buttons", [])

        self._folder_popup = FolderPopup(sub_buttons, theme, btn_size, label_mode, parent=self)
        self._folder_popup.button_clicked.connect(run_action)
        self._folder_popup.closed.connect(lambda: setattr(self, "_folder_popup", None))

        # 팝업 위치: 독 위치 기준 자동 계산
        pos = self._popup_position()
        self._folder_popup.move(pos)
        self._folder_popup.show()

    def _popup_position(self) -> QPoint:
        screen = QApplication.primaryScreen().geometry()
        dock_rect = self.geometry()

        # 기본: 독 위쪽
        x = dock_rect.left()
        y = dock_rect.top() - 100

        if self._snapped == "bottom" or dock_rect.bottom() > screen.height() * 0.7:
            y = dock_rect.top() - 110
        elif self._snapped in ("left", "right"):
            y = dock_rect.top()
            if self._snapped == "left":
                x = dock_rect.right() + 4
            else:
                x = dock_rect.left() - 250

        return QPoint(max(0, x), max(0, y))

    # ── 우클릭 컨텍스트 메뉴 ─────────────────────────────────────────────────

    def _on_right_click(self, button_data, global_pos: QPoint, row: int, col: int):
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())

        if button_data:
            edit_act = menu.addAction("✏️ 편집")
            edit_act.triggered.connect(lambda: self._edit_button(row, col))
            del_act = menu.addAction("🗑️ 삭제")
            del_act.triggered.connect(lambda: self._delete_button(row, col))
        else:
            add_act = menu.addAction("➕ 버튼 추가")
            add_act.triggered.connect(lambda: self._add_button_at(row, col))

        menu.exec(global_pos)

    # ── 버튼 CRUD ─────────────────────────────────────────────────────────────

    def _add_button_from_empty(self):
        cols = self.config.get("grid.cols", 3)
        rows = self.config.get("grid.rows", 2)
        pages = self.config.pages
        if not pages or self.current_page >= len(pages):
            return
        buttons = pages[self.current_page].get("buttons", [])
        idx = len(buttons)
        if idx >= rows * cols:
            return
        self._add_button_at(idx // cols, idx % cols)

    def _add_button_at(self, row: int, col: int):
        dlg = EditDialog(None, self)
        if dlg.exec():
            self._save_button_at(row, col, dlg.get_data())

    def _edit_button(self, row: int, col: int):
        cols = self.config.get("grid.cols", 3)
        idx = row * cols + col
        pages = self.config.pages
        if not pages or self.current_page >= len(pages):
            return
        buttons = pages[self.current_page].get("buttons", [])
        if idx >= len(buttons):
            return

        dlg = EditDialog(buttons[idx], self)
        if dlg.exec():
            self._save_button_at(row, col, dlg.get_data())

    def _save_button_at(self, row: int, col: int, data: dict):
        cols = self.config.get("grid.cols", 3)
        idx = row * cols + col
        pages = self.config.pages
        if not pages or self.current_page >= len(pages):
            return
        buttons = pages[self.current_page].setdefault("buttons", [])
        while len(buttons) <= idx:
            buttons.append(None)
        buttons[idx] = data
        self._trim_buttons(buttons)
        self.config.save_pages()
        self._refresh_buttons()

    def _delete_button(self, row: int, col: int):
        cols = self.config.get("grid.cols", 3)
        idx = row * cols + col
        pages = self.config.pages
        if not pages or self.current_page >= len(pages):
            return
        buttons = pages[self.current_page].get("buttons", [])
        if idx < len(buttons):
            buttons[idx] = None
            self._trim_buttons(buttons)
            self.config.save_pages()
            self._refresh_buttons()

    def _trim_buttons(self, buttons: list):
        while buttons and buttons[-1] is None:
            buttons.pop()

    # ── 전역 단축키 동기화 ────────────────────────────────────────────────────

    def _compute_hotkey_fp(self) -> frozenset:
        """모든 페이지의 핫키 집합을 지문(frozenset)으로 반환."""
        result = set()
        for page_idx, page in enumerate(self.config.pages):
            for btn in page.get("buttons", []):
                if btn and btn.get("action_type") == "text_paste":
                    hk = btn.get("hotkey", "").strip()
                    if hk:
                        result.add((hk, page_idx))
        return frozenset(result)

    def _sync_hotkeys(self):
        """
        모든 페이지의 text_paste 버튼 단축키를 등록한다.
        같은 단축키가 여러 페이지에 있어도 Windows에는 한 번만 등록하고,
        발동 시 현재 페이지(self.current_page)를 보고 해당 버튼을 실행한다.
        핫키 구성이 바뀌지 않으면 재등록을 생략한다.
        """
        new_fp = self._compute_hotkey_fp()
        if new_fp == self._last_hotkey_fp:
            return   # 변경 없음 → 재등록 불필요
        self._last_hotkey_fp = new_fp

        self._hotkey_manager.unregister_all()
        self._registered_hotkeys.clear()
        self._hotkey_table.clear()

        _hk_log("[sync] _sync_hotkeys 시작")

        # 1단계: 페이지별 테이블 구성
        for page_idx, page in enumerate(self.config.pages):
            for btn in page.get("buttons", []):
                if not btn:
                    continue
                if btn.get("action_type") != "text_paste":
                    continue
                hotkey = btn.get("hotkey", "").strip()
                if not hotkey:
                    continue
                _hk_log(f"[sync] 버튼 발견: page={page_idx} hotkey={hotkey!r} text={btn.get('text','')[:20]!r}")
                self._hotkey_table.setdefault(hotkey, {})[page_idx] = btn

        # 2단계: 고유 단축키만 Windows에 등록
        failed = []
        count = 0
        for hotkey in self._hotkey_table:
            def make_cb(hk=hotkey):
                return lambda: self._dispatch_hotkey(hk)

            ok, err_msg = self._hotkey_manager.register(hotkey, make_cb())
            if ok:
                self._registered_hotkeys.add(hotkey)
                count += 1
            else:
                failed.append((hotkey, err_msg))

        _hk_log(f"[sync] 완료: {count}개 등록, {len(failed)}개 실패")

        # 3단계: 등록 실패 팝업
        if failed:
            lines = "\n".join(f"• {hk}  →  {msg}" for hk, msg in failed)
            QMessageBox.warning(
                self, "단축키 등록 실패",
                f"다음 단축키를 등록하지 못했습니다:\n\n{lines}\n\n"
                "다른 프로그램이 이미 사용 중이거나 Windows 예약 단축키일 수 있습니다.\n"
                "버튼 편집에서 단축키를 변경해 주세요."
            )

    def _dispatch_hotkey(self, hotkey: str):
        """단축키 발동 시 현재 페이지에 해당하는 버튼을 실행"""
        page_map = self._hotkey_table.get(hotkey, {})
        btn = page_map.get(self.current_page)
        if btn is None:
            _hk_log(f"[dispatch] hotkey={hotkey!r} 현재 페이지({self.current_page})에 버튼 없음")
            return
        text   = btn.get("text", "")
        method = btn.get("paste_method", "clipboard")
        _hk_log(f"[dispatch] hotkey={hotkey!r} page={self.current_page} text={text[:20]!r}")
        import threading
        threading.Thread(target=paste_for_hotkey, args=(text, method), daemon=True).start()

    # ── 페이지 관리 ───────────────────────────────────────────────────────────

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_buttons(auto_size=False)

    def _next_page(self):
        if self.current_page < len(self.config.pages) - 1:
            self.current_page += 1
            self._refresh_buttons(auto_size=False)

    def _add_page(self):
        page_id = f"page_{uuid.uuid4().hex[:8]}"
        pages = self.config.pages
        pages.append({
            "id": page_id,
            "name": f"페이지 {len(pages) + 1}",
            "buttons": []
        })
        self.config.save_pages()
        self.current_page = len(pages) - 1
        self._refresh_buttons()

    def _del_page(self):
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                     QLabel, QPushButton)
        pages = self.config.pages
        if len(pages) <= 1:
            return  # 마지막 페이지는 삭제 불가
        page_name = pages[self.current_page].get("name", "현재 페이지")

        dlg = QDialog(self)
        dlg.setWindowTitle("페이지 삭제")
        dlg.setFixedWidth(300)
        dlg.setStyleSheet("""
            QDialog {
                background: #f5f5f5;
                color: #1a1a1a;
                font-family: '맑은 고딕', 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QLabel {
                background: transparent;
                color: #1a1a1a;
                font-size: 12px;
            }
            QPushButton {
                background: #ffffff;
                color: #1a1a1a;
                border: 1px solid #b0b0b0;
                border-radius: 4px;
                padding: 5px 16px;
                min-height: 26px;
                font-size: 12px;
            }
            QPushButton:hover { background: #e8f0fe; border-color: #0078d4; }
        """)

        vbox = QVBoxLayout(dlg)
        vbox.setContentsMargins(20, 16, 20, 14)
        vbox.setSpacing(12)

        lbl = QLabel(f"'{page_name}'을(를) 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.")
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)

        hbox = QHBoxLayout()
        hbox.setSpacing(8)
        hbox.addStretch()

        del_btn = QPushButton("삭제")
        del_btn.setStyleSheet(
            "background:#d32f2f; color:#ffffff; border:1px solid #b71c1c;"
            " border-radius:4px; padding:5px 16px; min-height:26px;"
            " font-size:12px; font-weight:bold;"
        )
        cancel_btn = QPushButton("취소")
        hbox.addWidget(del_btn)
        hbox.addWidget(cancel_btn)
        vbox.addLayout(hbox)

        confirmed = {"v": False}
        del_btn.clicked.connect(lambda: (confirmed.__setitem__("v", True), dlg.accept()))
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()

        if not confirmed["v"]:
            return
        del pages[self.current_page]
        self.config.save_pages()
        self.current_page = max(0, self.current_page - 1)
        self._refresh_buttons(auto_size=False)

    # ── 핀 / 설정 ─────────────────────────────────────────────────────────────

    def _do_minimize(self):
        self.hide()

    def _toggle_pin(self, checked: bool):
        self.config.set("pinned", checked)
        self.config.save_config()

    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._apply_theme()
            self._refresh_buttons()

    # ── 테마 적용 ─────────────────────────────────────────────────────────────

    def _apply_theme(self):
        theme = self.config.get("theme", {})
        bg = theme.get("background", "#1e1e2e")
        text = theme.get("text_color", "#cdd6f4")
        btn_c = theme.get("button_color", "#313244")
        btn_h = theme.get("button_hover", "#45475a")
        btn_p = theme.get("button_pressed", "#181825")
        accent = theme.get("accent_color", "#89b4fa")
        border = theme.get("border_color", "#585b70")

        opacity = self.config.get("opacity", 0.92)
        self.setWindowOpacity(opacity)

        self.setStyleSheet(f"""
            QWidget {{
                color: {text};
                font-family: '맑은 고딕', 'Segoe UI', sans-serif;
                font-size: 11px;
            }}
            QPushButton {{
                background: {btn_c};
                color: {text};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 1px 4px;
            }}
            QPushButton:hover {{ background: {btn_h}; }}
            QPushButton:pressed {{ background: {btn_p}; }}
            QPushButton:checked {{ background: {accent}; color: #fff; }}
            QPushButton#minimize_btn {{ background: #d4a017; color: #fff; border-color: #a07a10; }}
            QPushButton#minimize_btn:hover {{ background: #f0b929; }}
            QPushButton#close_btn {{ background: #c0392b; color: #fff; border-color: #922b21; }}
            QPushButton#close_btn:hover {{ background: #e74c3c; }}
            QPushButton#del_page_btn {{ background: #7a2020; color: #ffaaaa; border-color: #5a1515; }}
            QPushButton#del_page_btn:hover {{ background: #a33030; color: #fff; }}
            QLabel {{ background: transparent; color: {text}; }}
        """)
        self.update()

    # ── 위치 복원 / 저장 ──────────────────────────────────────────────────────

    def _restore_position(self):
        pos = self.config.get("position", {"x": -1, "y": -1})
        x, y = pos.get("x", -1), pos.get("y", -1)
        if x == -1 and y == -1:
            screen = QApplication.primaryScreen().geometry()
            self.adjustSize()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
        self.move(x, y)
        if self._snapped:
            self._snap_to_edge(self._snapped)

    def _save_position(self):
        p = self.pos()
        self.config.set("position", {"x": p.x(), "y": p.y()})
        self.config.set("snapped", self._snapped)
        self.config.save_config()

    # ── 가장자리 흡착 + 자동 숨김 ────────────────────────────────────────────

    def _snap_to_edge(self, edge: str):
        screen = QApplication.primaryScreen().geometry()
        if edge == "bottom":
            x = max(0, min(self.pos().x(), screen.width() - self.width()))
            self.move(x, screen.height() - self.height())
        elif edge == "left":
            self.move(0, self.pos().y())
        elif edge == "right":
            self.move(screen.width() - self.width(), self.pos().y())

    def _check_snap(self):
        screen = QApplication.primaryScreen().geometry()
        p = self.pos()
        w, h = self.width(), self.height()

        if p.y() + h >= screen.height() - SNAP_DISTANCE:
            self._snapped = "bottom"
            self._snap_to_edge("bottom")
        elif p.x() <= SNAP_DISTANCE:
            self._snapped = "left"
            self._snap_to_edge("left")
        elif p.x() + w >= screen.width() - SNAP_DISTANCE:
            self._snapped = "right"
            self._snap_to_edge("right")
        else:
            self._snapped = None

    # ── 시스템 트레이 ─────────────────────────────────────────────────────────

    def _setup_tray(self):
        pixmap = self._load_tray_icon(32)
        self._tray = QSystemTrayIcon(QIcon(pixmap), self)
        tray_menu = QMenu()
        tray_menu.setStyleSheet(self._menu_style())
        tray_menu.addAction("🖥 열기").triggered.connect(self._restore_from_tray)
        tray_menu.addSeparator()
        tray_menu.addAction("✕ 종료").triggered.connect(QApplication.quit)
        self._tray.setContextMenu(tray_menu)
        self._tray.setToolTip("알잘딱버튼")
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    @staticmethod
    def _load_tray_icon(size: int) -> QPixmap:
        """소스 PNG에서 트레이 아이콘 로드. 파일이 없으면 빈 픽스맵 반환."""
        import os, sys
        base = (sys._MEIPASS
                if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))
        png_path = os.path.join(base, "알잘딱버튼 이미지.png")
        pm = QPixmap(png_path)
        if not pm.isNull():
            return pm.scaled(size, size,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        # PNG 없을 경우 빈 픽스맵
        fallback = QPixmap(size, size)
        fallback.fill(QColor(0, 0, 0, 0))
        return fallback

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.show()
        self.raise_()

    def _menu_style(self) -> str:
        return """
            QMenu {
                background-color: #2a2a3e;
                color: #ffffff;
                border: 1px solid #89b4fa;
                border-radius: 6px;
                padding: 4px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 20px 7px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QMenu::separator {
                height: 1px;
                background: #45475a;
                margin: 3px 6px;
            }
        """

    def _setup_autohide(self):
        self._autohide_timer = QTimer()
        self._autohide_timer.setInterval(AUTOHIDE_INTERVAL)
        self._autohide_timer.timeout.connect(self._autohide_tick)
        self._autohide_timer.start()

    # ── 리사이즈 ─────────────────────────────────────────────────────────────

    def _setup_resize_timer(self):
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._on_resize_done)
        self.setMouseTracking(True)

    def _get_resize_edge(self, local_pos) -> str | None:
        """로컬 좌표 → 리사이즈 방향('r','l','b','rb','lb') 또는 None."""
        w, h = self.width(), self.height()
        on_r = local_pos.x() >= w - RESIZE_GRIP
        on_l = local_pos.x() <= RESIZE_GRIP
        on_b = local_pos.y() >= h - RESIZE_GRIP
        # 흡착된 방향은 리사이즈 불가
        if self._snapped == "right":
            on_r = False
        if self._snapped == "left":
            on_l = False
        if self._snapped in ("bottom", "top"):
            on_b = False
        if on_r and on_b:
            return "rb"
        if on_l and on_b:
            return "lb"
        if on_r:
            return "r"
        if on_l:
            return "l"
        if on_b:
            return "b"
        return None

    def _do_resize(self, global_pos):
        """드래그 중 창 크기 및 버튼 크기 실시간 업데이트."""
        delta = global_pos - self._resize_start_pos
        cols = self.config.get("grid.cols", 3)
        rows = self.config.get("grid.rows", 2)
        h_gap = (cols - 1) * 4
        v_gap = (rows - 1) * 4
        min_w = MIN_BTN_SIZE * cols + _H_FIXED + h_gap
        min_h = MIN_BTN_SIZE * rows + _V_FIXED + v_gap

        start_w = self._resize_start_size.width()
        start_h = self._resize_start_size.height()
        new_w = start_w
        new_h = start_h

        if self._resize_edge in ("r", "rb"):
            new_w = max(min_w, start_w + delta.x())
        if self._resize_edge in ("b", "rb", "lb"):
            new_h = max(min_h, start_h + delta.y())

        # 창 크기 변경 + 버튼 업데이트를 한 번에 그려 문구·이모지 지연 제거
        btn_size = self._calc_btn_size(new_w, new_h, self._resize_edge or "")
        self.setUpdatesEnabled(False)
        self._update_btn_sizes_fast(btn_size)
        if self._resize_edge in ("l", "lb"):
            # 왼쪽 리사이즈: 오른쪽 끝을 고정, 왼쪽 끝을 이동
            raw_w = start_w - delta.x()
            new_w = max(min_w, raw_w)
            new_x = self._resize_start_x + delta.x()
            if raw_w < min_w:
                new_x = self._resize_start_x + start_w - min_w
            self.setGeometry(new_x, self.y(), new_w, new_h)
        else:
            self.resize(new_w, new_h)
        self.setUpdatesEnabled(True)
        self.update()

    def _calc_btn_size(self, win_w: int, win_h: int, edge: str = "") -> int:
        cols = self.config.get("grid.cols", 3)
        rows = self.config.get("grid.rows", 2)
        bw = (win_w - _H_FIXED - (cols - 1) * 4) // cols
        bh = (win_h - _V_FIXED - (rows - 1) * 4) // rows
        if edge in ("r", "l"):
            return max(MIN_BTN_SIZE, bw)
        if edge == "b":
            return max(MIN_BTN_SIZE, bh)
        return max(MIN_BTN_SIZE, min(bw, bh))

    def _update_btn_sizes_fast(self, new_size: int):
        """그리드 안의 ButtonWidget을 재생성 없이 크기만 갱신."""
        from button_widget import ButtonWidget as _BW
        for i in range(self._grid_layout.count()):
            item = self._grid_layout.itemAt(i)
            if item and isinstance(item.widget(), _BW):
                item.widget().update_size(new_size)
        # 부모 그리드 레이아웃 즉시 강제 재계산 (문구·이모지 크기 지연 방지)
        self._grid_layout.invalidate()
        self._grid_layout.activate()
        self._grid_widget.update()

    def _on_resize_done(self):
        """드래그 종료 후 버튼 완전 재생성 + 설정 저장."""
        target_w = self.width()
        target_h = self.height()
        cols = self.config.get("grid.cols", 3)
        rows = self.config.get("grid.rows", 2)
        h_gap = (cols - 1) * 4
        v_gap = (rows - 1) * 4
        edge = self._last_resize_edge

        new_size = self._calc_btn_size(target_w, target_h, edge)
        self.config.set("button_size", new_size)
        self._refresh_buttons(auto_size=False)

        if edge in ("r", "l"):
            # 가로 리사이즈 → 높이를 버튼 크기에 맞게 스냅
            snap_h = new_size * rows + _V_FIXED + v_gap
            self.resize(target_w, snap_h)
        elif edge == "b":
            # 세로 리사이즈 → 너비를 버튼 크기에 맞게 스냅
            snap_w = new_size * cols + _H_FIXED + h_gap
            self.resize(snap_w, target_h)
        else:
            self.resize(target_w, target_h)

        self.config.save_config()

    def _autohide_tick(self):
        autohide = self.config.get("autohide", True)
        pinned = self.config.get("pinned", False)
        if self._resize_edge:   # 리사이즈 중 자동숨김 방지
            return
        if not autohide or pinned or not self._snapped:
            if self._hidden:
                self._do_show()
            return

        cursor = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        dock_rect = self.geometry()

        near_edge = False
        if self._snapped == "bottom":
            near_edge = cursor.y() >= screen.height() - SNAP_DISTANCE
        elif self._snapped == "left":
            near_edge = cursor.x() <= SNAP_DISTANCE
        elif self._snapped == "right":
            near_edge = cursor.x() >= screen.width() - SNAP_DISTANCE

        cursor_on_dock = dock_rect.contains(cursor)

        if (near_edge or cursor_on_dock) and self._hidden:
            self._do_show()
        elif not near_edge and not cursor_on_dock and not self._hidden:
            self._do_hide()

    def _do_hide(self):
        if self._folder_popup and self._folder_popup.isVisible():
            self._folder_popup.close()
        self._hidden = True
        screen = QApplication.primaryScreen().geometry()
        if self._snapped == "bottom":
            self.move(self.x(), screen.height() - HIDE_STRIP)
        elif self._snapped == "left":
            self.move(-self.width() + HIDE_STRIP, self.y())
        elif self._snapped == "right":
            self.move(screen.width() - HIDE_STRIP, self.y())

    def _do_show(self):
        self._hidden = False
        self._snap_to_edge(self._snapped)

    # ── 마우스 이벤트 (드래그) ────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.position().toPoint())
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_size = self.size()
                self._resize_start_x = self.x()
            else:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self._snapped = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        gpos = event.globalPosition().toPoint()
        lpos = event.position().toPoint()
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self._resize_edge:
                self._do_resize(gpos)
            elif self._drag_pos:
                self.move(gpos - self._drag_pos)
        else:
            # 커서 모양 업데이트
            edge = self._get_resize_edge(lpos)
            if edge == "rb":
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif edge == "lb":
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif edge in ("r", "l"):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edge == "b":
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._resize_edge:
                self._last_resize_edge = self._resize_edge  # 완료 후 스냅 방향
                self._resize_edge = None
                self._resize_start_pos = None
                self._resize_start_size = None
                self._resize_timer.stop()
                self._on_resize_done()
            else:
                self._drag_pos = None
                self._check_snap()
                self._save_position()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        menu.addAction("⚙️ 설정").triggered.connect(self._open_settings)
        menu.addAction("📄 페이지 추가").triggered.connect(self._add_page)
        menu.exec(event.globalPos())

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self._prev_page()
        else:
            self._next_page()

    # ── 렌더링 ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        theme = self.config.get("theme", {})
        bg = QColor(theme.get("background", "#1e1e2e"))
        # 약간의 투명도 처리는 setWindowOpacity로 이미 적용됨

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        painter.fillPath(path, bg)
        painter.end()

        super().paintEvent(event)
