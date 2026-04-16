"""
버튼 편집 다이얼로그
7가지 액션 타입을 탭 없이 콤보박스로 전환하여 편집
"""

import uuid
import random
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QComboBox, QRadioButton,
    QButtonGroup, QStackedWidget, QWidget, QFileDialog,
    QListWidget, QListWidgetItem, QDialogButtonBox, QMessageBox,
    QGroupBox, QScrollArea, QCheckBox, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QFont


# Windows 예약 단축키 목록 (등록 시도 자체가 실패하거나 충돌 가능성 높은 조합)
_WINDOWS_RESERVED = {
    "Win+L", "Win+D", "Win+E", "Win+R", "Win+Tab", "Win+P",
    "Win+I", "Win+A", "Win+S", "Win+K", "Win+X", "Win+M",
    "Win+H", "Win+Q", "Win+G", "Win+U", "Win+B", "Win+T",
    "Win+1", "Win+2", "Win+3", "Win+4", "Win+5",
    "Win+6", "Win+7", "Win+8", "Win+9", "Win+0",
    "Ctrl+Alt+Del", "Ctrl+Esc", "Alt+Tab", "Alt+Shift+Tab",
    "Alt+F4", "Alt+Esc",
}

# 주요 사무용 앱 단축키 (충돌 시 문구가 출력되지 않을 수 있음)
# 수정자 순서: Ctrl → Alt → Shift (코드 내 파싱 순서 기준)
_APP_SHORTCUTS: dict[str, str] = {
    # ── Ctrl+Shift+Letter ──
    "Ctrl+Shift+A": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+B": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+C": "한글(HWP), 파워포인트",
    "Ctrl+Shift+D": "한글(HWP), 파워포인트",
    "Ctrl+Shift+E": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+F": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+G": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+H": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+I": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+J": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+K": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+L": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+M": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+N": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+O": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+P": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+Q": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+R": "한글(HWP), 파워포인트",
    "Ctrl+Shift+S": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+T": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+U": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+V": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+W": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+X": "파워포인트",
    "Ctrl+Shift+Y": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Shift+Z": "한글(HWP), 엑셀, 파워포인트",
    # ── Ctrl+Shift+Number ──
    "Ctrl+Shift+0": "엑셀",
    "Ctrl+Shift+1": "한글(HWP), 파워포인트",
    "Ctrl+Shift+2": "한글(HWP), 파워포인트",
    "Ctrl+Shift+3": "한글(HWP)",
    "Ctrl+Shift+4": "한글(HWP)",
    "Ctrl+Shift+5": "한글(HWP), 파워포인트",
    "Ctrl+Shift+6": "한글(HWP)",
    "Ctrl+Shift+7": "한글(HWP)",
    "Ctrl+Shift+8": "한글(HWP)",
    "Ctrl+Shift+9": "엑셀",
    # ── Ctrl+Alt+Letter ──
    "Ctrl+Alt+A": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+B": "한글(HWP), 파워포인트",
    "Ctrl+Alt+C": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+D": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+E": "한글(HWP), 파워포인트",
    "Ctrl+Alt+F": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+G": "한글(HWP), 파워포인트",
    "Ctrl+Alt+H": "한글(HWP), 파워포인트",
    "Ctrl+Alt+I": "한글(HWP), 파워포인트",
    "Ctrl+Alt+J": "파워포인트",
    "Ctrl+Alt+K": "한글(HWP), 파워포인트",
    "Ctrl+Alt+L": "엑셀, 파워포인트",
    "Ctrl+Alt+M": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+N": "한글(HWP), 파워포인트",
    "Ctrl+Alt+O": "파워포인트",
    "Ctrl+Alt+P": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+Q": "파워포인트",
    "Ctrl+Alt+R": "한글(HWP), 파워포인트",
    "Ctrl+Alt+S": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+T": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+U": "한글(HWP), 파워포인트",
    "Ctrl+Alt+V": "한글(HWP), 엑셀, 파워포인트",
    "Ctrl+Alt+W": "한글(HWP), 파워포인트",
    "Ctrl+Alt+X": "한글(HWP), 파워포인트",
    "Ctrl+Alt+Y": "한글(HWP), 파워포인트",
    "Ctrl+Alt+Z": "한글(HWP), 파워포인트",
    # ── Ctrl+Alt+Number ──
    "Ctrl+Alt+1": "엑셀",
    "Ctrl+Alt+2": "엑셀",
    "Ctrl+Alt+3": "엑셀",
    "Ctrl+Alt+4": "엑셀",
    "Ctrl+Alt+6": "엑셀",
    # ── Alt+Shift+Letter ──
    "Alt+Shift+A": "한글(HWP), 엑셀, 파워포인트",
    "Alt+Shift+B": "한글(HWP), 파워포인트",
    "Alt+Shift+C": "한글(HWP), 엑셀, 파워포인트",
    "Alt+Shift+D": "한글(HWP), 엑셀, 파워포인트",
    "Alt+Shift+E": "한글(HWP), 엑셀",
    "Alt+Shift+F": "한글(HWP), 엑셀, 파워포인트",
    "Alt+Shift+G": "한글(HWP)",
    "Alt+Shift+H": "한글(HWP), 파워포인트",
    "Alt+Shift+I": "한글(HWP), 엑셀",
    "Alt+Shift+J": "한글(HWP)",
    "Alt+Shift+K": "한글(HWP)",
    "Alt+Shift+L": "한글(HWP), 엑셀",
    "Alt+Shift+M": "한글(HWP), 엑셀",
    "Alt+Shift+N": "한글(HWP), 엑셀, 파워포인트",
    "Alt+Shift+O": "한글(HWP), 엑셀",
    "Alt+Shift+P": "한글(HWP), 엑셀, 파워포인트",
    "Alt+Shift+R": "한글(HWP), 엑셀",
    "Alt+Shift+S": "한글(HWP)",
    "Alt+Shift+T": "한글(HWP), 엑셀",
    "Alt+Shift+U": "한글(HWP), 엑셀",
    "Alt+Shift+V": "한글(HWP), 파워포인트",
    "Alt+Shift+W": "한글(HWP), 엑셀",
    "Alt+Shift+X": "엑셀",
    "Alt+Shift+Y": "한글(HWP), 엑셀",
    "Alt+Shift+Z": "한글(HWP), 엑셀",
    # ── Alt+Shift+Number ──
    "Alt+Shift+0": "엑셀",
    "Alt+Shift+1": "파워포인트",
    "Alt+Shift+2": "파워포인트",
    "Alt+Shift+3": "파워포인트",
    "Alt+Shift+4": "파워포인트",
    "Alt+Shift+5": "파워포인트",
    "Alt+Shift+6": "파워포인트",
    "Alt+Shift+7": "파워포인트",
    "Alt+Shift+9": "파워포인트",
}


DIALOG_STYLE = """
    QDialog, QWidget {
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
    QLineEdit {
        background: #ffffff;
        color: #1a1a1a;
        border: 1px solid #b0b0b0;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    QLineEdit:focus {
        border-color: #0078d4;
    }
    QPlainTextEdit {
        background: #ffffff;
        color: #1a1a1a;
        border: 1px solid #b0b0b0;
        border-radius: 4px;
        padding: 4px 8px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    QPlainTextEdit:focus {
        border-color: #0078d4;
    }
    QComboBox {
        background: #ffffff;
        color: #1a1a1a;
        border: 1px solid #b0b0b0;
        border-radius: 4px;
        padding: 3px 8px;
        min-height: 26px;
    }
    QComboBox QAbstractItemView {
        background: #ffffff;
        color: #1a1a1a;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
        outline: none;
    }
    QRadioButton {
        color: #1a1a1a;
        spacing: 6px;
    }
    QRadioButton::indicator {
        width: 14px;
        height: 14px;
        border: 1px solid #b0b0b0;
        border-radius: 7px;
        background: #ffffff;
    }
    QRadioButton::indicator:checked {
        background: #0078d4;
        border-color: #0078d4;
    }
    QCheckBox {
        color: #1a1a1a;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 14px;
        height: 14px;
        border: 1px solid #b0b0b0;
        border-radius: 3px;
        background: #ffffff;
    }
    QCheckBox::indicator:checked {
        background: #0078d4;
        border-color: #0078d4;
    }
    QListWidget {
        background: #ffffff;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background: #0078d4;
        color: #ffffff;
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
"""

# ── SVG 아이콘 임시 파일 생성 ────────────────────────────────────────────────
_COMBO_ARROW_PATH = ""
_CHECK_PATH = ""
_RADIO_PATH = ""
try:
    import tempfile as _tf
    _td = _tf.gettempdir()

    _p = _td + "/vr_combo_arrow.svg"
    with open(_p, "wb") as _f:
        _f.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 6">'
                 b'<polygon points="0,0 10,0 5,6" fill="#555555"/></svg>')
    _COMBO_ARROW_PATH = _p.replace("\\", "/")

    _p = _td + "/vr_check.svg"
    with open(_p, "wb") as _f:
        _f.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14">'
                 b'<polyline points="2,7 5,11 12,3" fill="none" stroke="#ffffff"'
                 b' stroke-width="2.2" stroke-linecap="round"'
                 b' stroke-linejoin="round"/></svg>')
    _CHECK_PATH = _p.replace("\\", "/")

    _p = _td + "/vr_radio.svg"
    with open(_p, "wb") as _f:
        _f.write(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 14 14">'
                 b'<circle cx="7" cy="7" r="6" fill="#0078d4" stroke="#0078d4"/>'
                 b'<circle cx="7" cy="7" r="3" fill="#ffffff"/></svg>')
    _RADIO_PATH = _p.replace("\\", "/")
except Exception:
    pass

DIALOG_STYLE += f"""
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 22px;
        border-left: 1px solid #c0c0c0;
        border-radius: 0 4px 4px 0;
        background: #ebebeb;
    }}
    QComboBox::down-arrow {{
        image: url({_COMBO_ARROW_PATH});
        width: 10px;
        height: 6px;
    }}
    QCheckBox::indicator:checked {{
        background: #0078d4;
        border-color: #0078d4;
        image: url({_CHECK_PATH});
    }}
    QRadioButton::indicator:checked {{
        image: url({_RADIO_PATH});
        border: none;
        background: transparent;
    }}
"""


EMOJI_CATEGORIES = {
    "감정": [
        "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃", "😉", "😊",
        "😇", "🥰", "😍", "🤩", "😘", "😗", "😚", "😙", "🥲", "😋", "😛", "😜",
        "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔", "😐", "😑", "😶", "😏", "😒",
        "🙄", "😬", "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕", "🤢", "🤧",
        "🥵", "🥶", "🥴", "😵", "🤯", "🥳", "🥸", "😎", "🤓", "🧐", "😕", "😟",
        "🙁", "☹️", "😮", "😯", "😲", "😳", "🥺", "😦", "😧", "😨", "😰", "😥",
        "😢", "😭", "😱", "😖", "😣", "😞", "😓", "😩", "😫", "🥱", "😤", "😡",
        "😠", "🤬", "😈", "👿", "💀", "☠️", "💩", "🤡", "👻", "🤖",
    ],
    "사람": [
        "👋", "🤚", "✋", "🖐️", "👌", "🤌", "✌️", "🤞", "🤟", "🤘", "🤙",
        "👈", "👉", "👆", "👇", "☝️", "👍", "👎", "✊", "👊", "🤜", "🤛",
        "👏", "🙌", "🤲", "🙏", "✍️", "💅", "🫶", "🫂",
        "👶", "🧒", "👦", "👧", "🧑", "👨", "👩", "🧓", "👴", "👵",
        "👨‍💼", "👩‍💼", "🧑‍🏫", "👨‍🏫", "👩‍🏫", "👨‍🎓", "👩‍🎓",
        "🧑‍💻", "👨‍💻", "👩‍💻", "👮", "💂", "🕵️", "👨‍⚕️", "👩‍⚕️",
    ],
    "자연": [
        "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮",
        "🐷", "🐸", "🐵", "🙈", "🙉", "🙊", "🐔", "🐧", "🐦", "🦆", "🦅", "🦉",
        "🦋", "🐛", "🐝", "🐌", "🐞", "🐜", "🦗",
        "🌸", "🌺", "🌻", "🌹", "🌷", "🌼", "🍀", "🌿", "🌱", "🌲", "🌳", "🌴",
        "🍁", "🍂", "🍃", "🌾", "🌵",
        "☀️", "🌤️", "⛅", "🌧️", "⛈️", "🌩️", "❄️", "⛄", "🌈", "🌊", "🌀",
        "🌙", "🌛", "🌜", "⭐", "🌟", "💫", "✨", "🔥", "💧", "🌍", "🌏",
    ],
    "음식": [
        "🍎", "🍊", "🍋", "🍇", "🍓", "🫐", "🍒", "🍑", "🥭", "🍍", "🥝", "🍅",
        "🍆", "🥑", "🥦", "🥕", "🌽", "🥔", "🍠", "🧅", "🧄",
        "🍔", "🍟", "🌭", "🍕", "🌮", "🌯", "🥗", "🥘", "🍲",
        "🍜", "🍝", "🍛", "🍣", "🍱", "🍤", "🍙", "🍚", "🍘", "🍥", "🥟",
        "🍰", "🎂", "🧁", "🍩", "🍪", "🍫", "🍬", "🍭", "🍡", "🍧", "🍨", "🍦",
        "☕", "🍵", "🧋", "🥤", "🍺", "🍻", "🥂", "🍷", "🍸", "🍹", "🧃", "🥛",
    ],
    "사무": [
        "📝", "📄", "📋", "📊", "📈", "📉", "📁", "📂", "📌", "📍",
        "✏️", "🖊️", "🖋️", "📏", "📐", "📎", "🖇️", "✂️", "🖍️",
        "📚", "📖", "🔖", "🗒️", "🗓️", "📅", "📆", "🗑️", "🗂️",
        "💻", "🖥️", "⌨️", "🖱️", "💾", "🖨️", "🔌", "💿", "📀",
        "📱", "☎️", "📞", "📟", "📠", "📷", "📸", "📹", "🎥", "📺", "📻",
        "📧", "✉️", "📩", "📨", "📬", "📭", "📮", "💬", "💭", "🗯️",
        "🔔", "📣", "📢", "🔕",
        "🎓", "🏫", "🧪", "🔬", "🔭", "🗺️", "🧮",
        "⚙️", "🔧", "🔨", "🛠️", "🔑", "🗝️", "🔒", "🔓",
        "💡", "🔦", "🕯️", "💰", "💳", "📦", "🎁", "🛒",
    ],
    "기호": [
        "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️",
        "✅", "❎", "❌", "⚠️", "❓", "❗", "‼️", "💯", "🔥", "💥",
        "🎯", "🏆", "🥇", "🥈", "🥉", "🎖️", "🏅",
        "🎉", "🎊", "🎈", "🎀", "🎗️", "🎁",
        "🚀", "⭐", "🌟", "🌈", "☀️",
        "⬆️", "⬇️", "⬅️", "➡️", "↗️", "↘️", "↙️", "↖️", "🔄", "🔃",
        "▶️", "⏸️", "⏹️", "⏺️", "⏭️", "⏮️",
        "🔊", "🔇", "🔕", "🚫", "⛔",
        "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
        "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣", "#️⃣", "*️⃣",
        "🅰️", "🅱️", "🆎", "🆑", "🆒", "🆓", "🆕", "🆖", "🆗", "🆙", "🆚",
        "🉐", "㊙️", "㊗️", "🈵", "🈹", "🈶", "🈚",
        "✔️", "☑️", "🔘", "🔲", "🔳", "⚫", "⚪", "🟥", "🟧", "🟨",
        "🟩", "🟦", "🟪", "🟫", "⬛", "⬜",
    ],
}

# 하위 호환 — 전체 이모지 단순 목록 (아이콘 랜덤 선택 등에서 사용)
_seen: set = set()
EMOJI_POOL: list = []
for _cat_emojis in EMOJI_CATEGORIES.values():
    for _e in _cat_emojis:
        if _e not in _seen:
            _seen.add(_e)
            EMOJI_POOL.append(_e)


class EmojiPickerDialog(QDialog):
    """이모지 선택 팝업 — 카테고리 탭 + 스크롤 격자"""
    COLS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("이모지 선택")
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedWidth(360)
        self.setStyleSheet("""
            QDialog { background: #ffffff; border: 1px solid #b0b0b0;
                      border-radius: 6px; }
            QPushButton#catBtn {
                background: #f0f0f0; border: 1px solid #d0d0d0;
                border-radius: 4px; font-size: 10px;
                padding: 3px 4px; min-height: 20px;
            }
            QPushButton#catBtn:checked {
                background: #0078d4; color: #ffffff; border-color: #005a9e;
            }
            QPushButton#catBtn:hover:!checked { background: #e0e8ff; }
            QScrollArea { border: none; }
        """)
        self.selected: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 카테고리 탭 버튼 행
        cat_row = QHBoxLayout()
        cat_row.setSpacing(3)
        self._cat_btns: dict = {}
        for cat_name in EMOJI_CATEGORIES:
            btn = QPushButton(cat_name)
            btn.setObjectName("catBtn")
            btn.setCheckable(True)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(lambda _, c=cat_name: self._switch_cat(c))
            cat_row.addWidget(btn)
            self._cat_btns[cat_name] = btn
        layout.addLayout(cat_row)

        # 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(252)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(2)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_widget)
        layout.addWidget(self._scroll)

        # 첫 번째 카테고리로 초기화
        first_cat = next(iter(EMOJI_CATEGORIES))
        self._switch_cat(first_cat)

    def _switch_cat(self, name: str):
        for cat, btn in self._cat_btns.items():
            btn.setChecked(cat == name)
        self._fill(name)
        self._scroll.verticalScrollBar().setValue(0)

    def _fill(self, cat: str):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, emoji in enumerate(EMOJI_CATEGORIES[cat]):
            btn = QPushButton(emoji)
            btn.setFixedSize(38, 38)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet("""
                QPushButton { background: transparent; border: 1px solid transparent;
                              border-radius: 4px; font-size: 20px; padding: 0px; }
                QPushButton:hover { background: #e8f0fe; border-color: #0078d4; }
            """)
            btn.clicked.connect(lambda _, e=emoji: self._pick(e))
            self._grid.addWidget(btn, i // self.COLS, i % self.COLS)

    def _pick(self, emoji: str):
        self.selected = emoji
        self.accept()


class _DynStack(QStackedWidget):
    """현재 페이지 크기만 보고하는 QStackedWidget — 다이얼로그 동적 리사이즈용"""

    def sizeHint(self):
        w = self.currentWidget()
        return w.sizeHint() if w else super().sizeHint()

    def minimumSizeHint(self):
        w = self.currentWidget()
        return w.minimumSizeHint() if w else super().minimumSizeHint()


ACTION_TYPES = [
    ("text_paste",    "📝 텍스트 붙여넣기"),
    ("folder_open",   "📁 폴더 열기"),
    ("file_open",     "📄 파일 열기"),
    ("url_open",      "🌐 URL 열기"),
    ("app_run",       "🚀 프로그램 실행"),
    ("folder_button", "📂 폴더형 버튼"),
    ("emoji_insert",  "😊 이모지 삽입"),
]


class ShortcutRecorder(QLineEdit):
    """클릭 후 키보드 눌러서 단축키 녹화"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("클릭 후 단축키를 눌러주세요 (예: Ctrl+C)")
        self.setReadOnly(True)

    def keyPressEvent(self, event):
        mods = event.modifiers()
        key = event.key()

        # 단독 수정자 키는 무시
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Alt,
                   Qt.Key.Key_Shift, Qt.Key.Key_Meta):
            return

        parts = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if mods & Qt.KeyboardModifier.MetaModifier:
            parts.append("Win")

        # nativeVirtualKey()로 Shift 영향 없이 물리 키 코드 획득
        # (Shift+1 → VK=0x31 → "1",  Shift+8 → VK=0x38 → "8")
        vk = event.nativeVirtualKey()
        if vk and 0x20 < vk < 0x100:
            if 0x30 <= vk <= 0x39:      # 숫자 0-9
                key_str = chr(vk)
            elif 0x41 <= vk <= 0x5A:    # 알파벳 A-Z
                key_str = chr(vk)
            elif 0x70 <= vk <= 0x7B:    # F1-F12
                key_str = f"F{vk - 0x6F}"
            else:
                key_str = QKeySequence(key).toString()
        else:
            key_str = QKeySequence(key).toString()

        if key_str:
            parts.append(key_str)

        if parts:
            combo = "+".join(parts)
            self.setText(combo)
            # Windows 예약 단축키 경고 (등록 자체가 실패할 가능성 높음)
            if combo in _WINDOWS_RESERVED:
                QMessageBox.warning(
                    self, "Windows 예약 단축키",
                    f"'{combo}'은(는) Windows 시스템 단축키입니다.\n"
                    "등록에 실패할 수 있으니 다른 단축키를 사용하세요."
                )
            # 앱 단축키 충돌 경고 (해당 앱 사용 중일 때 문구가 출력되지 않을 수 있음)
            elif combo in _APP_SHORTCUTS:
                apps = _APP_SHORTCUTS[combo]
                QMessageBox.information(
                    self, "앱 단축키 충돌 주의",
                    f"'{combo}'은(는) {apps}에서 사용하는 단축키입니다.\n\n"
                    "해당 앱이 활성화된 상태에서는 앱의 기능이 실행되어\n"
                    "문구가 출력되지 않을 수 있습니다.\n\n"
                    "다른 단축키를 사용하거나, 토스트 알림으로 확인하세요."
                )


class SubButtonEditor(QDialog):
    """폴더형 버튼의 하위 버튼 편집"""

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("하위 버튼 편집")
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_STYLE)
        self._data = data or {}

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.icon_edit = QLineEdit(self._data.get("icon", ""))
        self.label_edit = QLineEdit(self._data.get("label", ""))

        layout.addRow("아이콘 (이모지):", self.icon_edit)
        layout.addRow("버튼 이름:", self.label_edit)

        # 액션 타입 (폴더형 제외)
        self.type_combo = QComboBox()
        for val, text in ACTION_TYPES:
            if val != "folder_button":
                self.type_combo.addItem(text, val)
        cur_type = self._data.get("action_type", "url_open")
        idx = next((i for i, (v, _) in enumerate(ACTION_TYPES)
                    if v == cur_type and v != "folder_button"), 0)
        self.type_combo.setCurrentIndex(idx)
        layout.addRow("기능:", self.type_combo)

        # 값 입력 행 (QLineEdit + 찾기 버튼)
        value_row = QHBoxLayout()
        self.value_edit = QLineEdit()
        self._browse_btn = QPushButton("찾기")
        self._browse_btn.setFixedWidth(52)
        value_row.addWidget(self.value_edit)
        value_row.addWidget(self._browse_btn)
        layout.addRow("값:", value_row)

        # 초기값 채우기
        key = self._get_value_key(cur_type)
        self.value_edit.setText(self._data.get(key, ""))
        self._update_browse_btn(cur_type)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._browse_btn.clicked.connect(self._browse_value)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _get_value_key(self, action_type):
        return {
            "text_paste": "text",
            "folder_open": "path",
            "file_open": "path",
            "url_open": "url",
            "app_run": "path",
            "shortcut": "shortcut",
        }.get(action_type, "value")

    def _update_browse_btn(self, action_type):
        """경로 탐색이 필요한 타입만 찾기 버튼 활성화"""
        needs_browse = action_type in ("folder_open", "file_open", "app_run")
        self._browse_btn.setVisible(needs_browse)
        placeholder = {
            "text_paste": "붙여넣을 텍스트",
            "folder_open": "폴더 경로 (예: C:\\Users\\문서)",
            "file_open": "파일 경로",
            "url_open": "https://www.example.com",
            "app_run": "실행 파일 경로 (.exe)",
            "shortcut": "예: Ctrl+C",
        }.get(action_type, "")
        self.value_edit.setPlaceholderText(placeholder)

    def _on_type_changed(self, _):
        self.value_edit.clear()
        action_type = self.type_combo.currentData()
        self._update_browse_btn(action_type)

    def _browse_value(self):
        action_type = self.type_combo.currentData()
        if action_type == "folder_open":
            path = QFileDialog.getExistingDirectory(self, "폴더 선택")
            if path:
                self.value_edit.setText(path)
        elif action_type == "file_open":
            path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
            if path:
                self.value_edit.setText(path)
        elif action_type == "app_run":
            path, _ = QFileDialog.getOpenFileName(
                self, "프로그램 선택", "",
                "실행 파일 (*.exe *.bat *.cmd *.lnk);;모든 파일 (*)")
            if path:
                self.value_edit.setText(path)

    def get_data(self):
        action_type = self.type_combo.currentData()
        value_key = self._get_value_key(action_type)
        return {
            "id": self._data.get("id", f"btn_{uuid.uuid4().hex[:8]}"),
            "icon": self.icon_edit.text().strip() or random.choice(EMOJI_POOL),
            "label": self.label_edit.text().strip(),
            "action_type": action_type,
            value_key: self.value_edit.text().strip(),
        }


class EditDialog(QDialog):
    """메인 버튼 편집 다이얼로그"""

    def __init__(self, button_data=None, parent=None):
        super().__init__(parent)
        self.button_data = button_data or {}
        self.setWindowTitle("버튼 편집" if button_data else "버튼 추가")
        self.setMinimumWidth(440)
        self.setStyleSheet(DIALOG_STYLE)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # ─ 기본 정보 ─
        form = QFormLayout()
        icon_row = QHBoxLayout()
        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("비우면 랜덤 이모지 자동 선택")
        emoji_pick_btn = QPushButton("😊")
        emoji_pick_btn.setToolTip("이모지 선택")
        emoji_pick_btn.setFixedWidth(36)
        emoji_pick_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        emoji_pick_btn.clicked.connect(self._open_emoji_picker)
        icon_row.addWidget(self.icon_edit)
        icon_row.addWidget(emoji_pick_btn)
        form.addRow("아이콘:", icon_row)

        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("버튼 이름")
        form.addRow("버튼 이름:", self.label_edit)

        # 이미지 파일
        img_row = QHBoxLayout()
        self.image_edit = QLineEdit()
        self.image_edit.setPlaceholderText("이미지 파일 경로 (선택)")
        img_browse = QPushButton("찾기")
        img_browse.setFixedWidth(50)
        img_browse.clicked.connect(self._browse_image)
        img_row.addWidget(self.image_edit)
        img_row.addWidget(img_browse)
        form.addRow("이미지:", img_row)

        main_layout.addLayout(form)

        # ─ 액션 타입 선택 ─
        type_label = QLabel("기능 선택:")
        main_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        for val, text in ACTION_TYPES:
            self.type_combo.addItem(text, val)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        main_layout.addWidget(self.type_combo)

        # ─ 타입별 설정 패널 (스택) ─
        self.stack = _DynStack()
        self.stack.addWidget(self._make_text_paste_panel())    # 0
        self.stack.addWidget(self._make_path_panel("폴더"))    # 1
        self.stack.addWidget(self._make_path_panel("파일"))    # 2
        self.stack.addWidget(self._make_url_panel())           # 3
        self.stack.addWidget(self._make_path_panel("앱"))      # 4
        self.stack.addWidget(self._make_folder_btn_panel())    # 5
        self.stack.addWidget(self._make_emoji_insert_panel())  # 6
        main_layout.addWidget(self.stack)

        # ─ OK / Cancel ─
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    # ── 각 타입별 패널 ────────────────────────────────────────────────────────

    def _make_text_paste_panel(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("붙여넣을 텍스트\n(여러 줄 입력 가능, 엔터와 띄어쓰기 그대로 반영됩니다)")
        self.text_edit.setMinimumHeight(120)
        layout.addRow("텍스트:", self.text_edit)

        method_group = QButtonGroup(w)
        self.radio_clipboard = QRadioButton("타입1: 클립보드 붙여넣기 (Ctrl+V) — 권장")
        self.radio_type = QRadioButton("타입2: 한 글자씩 타이핑")
        self.radio_clipboard.setChecked(True)
        method_group.addButton(self.radio_clipboard)
        method_group.addButton(self.radio_type)
        layout.addRow("방식:", self.radio_clipboard)
        layout.addRow("", self.radio_type)

        self.text_hotkey_recorder = ShortcutRecorder()
        layout.addRow("전역 단축키:", self.text_hotkey_recorder)

        hint = QLabel("단축키를 지정하면 어떤 창에서든 해당 단축키로 문구를 입력할 수 있습니다")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 10px;")
        layout.addRow("", hint)
        return w

    def _make_path_panel(self, kind: str):
        w = QWidget()
        layout = QHBoxLayout(w)
        edit = QLineEdit()
        edit.setPlaceholderText(f"{kind} 경로")
        browse = QPushButton("찾기")
        browse.setFixedWidth(50)

        layout.addWidget(edit)
        layout.addWidget(browse)

        # 각각 저장
        if kind == "폴더":
            self.folder_path_edit = edit
            browse.clicked.connect(
                lambda: self._browse_dir(self.folder_path_edit))
        elif kind == "파일":
            self.file_path_edit = edit
            browse.clicked.connect(
                lambda: self._browse_file(self.file_path_edit))
        else:  # 앱
            self.app_path_edit = edit
            browse.clicked.connect(
                lambda: self._browse_app(self.app_path_edit))
        return w

    def _make_url_panel(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.example.com")
        layout.addRow("URL:", self.url_edit)
        return w

    def _make_folder_btn_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        label = QLabel("하위 버튼 목록:")
        layout.addWidget(label)

        self.sub_list = QListWidget()
        self.sub_list.setMaximumHeight(120)
        layout.addWidget(self.sub_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ 추가")
        edit_btn = QPushButton("✏️ 편집")
        del_btn = QPushButton("🗑️ 삭제")
        add_btn.clicked.connect(self._add_sub_button)
        edit_btn.clicked.connect(self._edit_sub_button)
        del_btn.clicked.connect(self._del_sub_button)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        self._sub_buttons = []
        return w

    def _make_emoji_insert_panel(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 8, 4, 4)
        desc = QLabel(
            "버튼을 클릭하면 이모지 선택창이 열리고,\n"
            "선택한 이모지가 현재 커서 위치에 자동으로 삽입됩니다.\n"
            "이모지 단축키(Win+.)를 몰라도 사용할 수 있습니다."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(desc)
        layout.addStretch()
        return w

    def _make_shortcut_panel(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.shortcut_recorder = ShortcutRecorder()
        layout.addRow("단축키:", self.shortcut_recorder)
        hint = QLabel("버튼 클릭 후 원하는 단축키를 눌러주세요")
        hint.setStyleSheet("color: gray; font-size: 10px;")
        layout.addRow("", hint)
        return w

    # ── 파일 탐색 ─────────────────────────────────────────────────────────────

    def _open_emoji_picker(self):
        dlg = EmojiPickerDialog(self)
        dlg.adjustSize()  # 크기 확정 후 위치 계산
        btn = self.sender()
        if btn:
            pos = btn.mapToGlobal(btn.rect().bottomLeft())
            screen = QApplication.primaryScreen().availableGeometry()
            x = min(pos.x(), screen.right() - dlg.width())
            y = min(pos.y(), screen.bottom() - dlg.height())
            x = max(x, screen.left())
            y = max(y, screen.top())
            dlg.move(x, y)
        if dlg.exec() and dlg.selected:
            self.icon_edit.setText(dlg.selected)

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "",
            "이미지 파일 (*.png *.jpg *.jpeg *.bmp *.ico *.svg)")
        if path:
            self.image_edit.setText(path)

    def _browse_dir(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if path:
            edit.setText(path)

    def _browse_file(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
        if path:
            edit.setText(path)

    def _browse_app(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "프로그램 선택", "",
            "실행 파일 (*.exe *.bat *.cmd *.lnk);;모든 파일 (*)")
        if path:
            edit.setText(path)

    # ── 하위 버튼 편집 ────────────────────────────────────────────────────────

    def _add_sub_button(self):
        dlg = SubButtonEditor(parent=self)
        if dlg.exec():
            data = dlg.get_data()
            self._sub_buttons.append(data)
            self._refresh_sub_list()

    def _edit_sub_button(self):
        row = self.sub_list.currentRow()
        if row < 0 or row >= len(self._sub_buttons):
            return
        dlg = SubButtonEditor(self._sub_buttons[row], parent=self)
        if dlg.exec():
            self._sub_buttons[row] = dlg.get_data()
            self._refresh_sub_list()

    def _del_sub_button(self):
        row = self.sub_list.currentRow()
        if 0 <= row < len(self._sub_buttons):
            del self._sub_buttons[row]
            self._refresh_sub_list()

    def _refresh_sub_list(self):
        self.sub_list.clear()
        for btn in self._sub_buttons:
            icon = btn.get("icon", "")
            label = btn.get("label", "")
            action = btn.get("action_type", "")
            self.sub_list.addItem(f"{icon} {label}  [{action}]")

    # ── 데이터 로드/저장 ──────────────────────────────────────────────────────

    def _load_data(self):
        d = self.button_data
        self.icon_edit.setText(d.get("icon", ""))
        self.label_edit.setText(d.get("label", ""))
        self.image_edit.setText(d.get("image_path", ""))

        action_type = d.get("action_type", "text_paste")
        type_index = next((i for i, (v, _) in enumerate(ACTION_TYPES)
                           if v == action_type), 0)
        self.type_combo.setCurrentIndex(type_index)
        self.stack.setCurrentIndex(type_index)

        # 각 필드 채우기
        self.text_edit.setPlainText(d.get("text", ""))
        method = d.get("paste_method", "clipboard")
        if method == "type":
            self.radio_type.setChecked(True)
        else:
            self.radio_clipboard.setChecked(True)
        self.text_hotkey_recorder.setText(d.get("hotkey", ""))

        self.folder_path_edit.setText(d.get("path", "") if action_type == "folder_open" else "")
        self.file_path_edit.setText(d.get("path", "") if action_type == "file_open" else "")
        self.app_path_edit.setText(d.get("path", "") if action_type == "app_run" else "")
        self.url_edit.setText(d.get("url", ""))

        self._sub_buttons = list(d.get("sub_buttons", []))
        self._refresh_sub_list()

    def _on_type_changed(self, index):
        self.stack.setCurrentIndex(index)
        self.adjustSize()

    def get_data(self) -> dict:
        action_type = self.type_combo.currentData()
        data = {
            "id": self.button_data.get("id", f"btn_{uuid.uuid4().hex[:8]}"),
            "icon": self.icon_edit.text().strip() or random.choice(EMOJI_POOL),
            "label": self.label_edit.text().strip(),
            "image_path": self.image_edit.text().strip(),
            "action_type": action_type,
        }

        if action_type == "text_paste":
            data["text"] = self.text_edit.toPlainText()
            data["paste_method"] = "type" if self.radio_type.isChecked() else "clipboard"
            data["hotkey"] = self.text_hotkey_recorder.text().strip()
        elif action_type == "folder_open":
            data["path"] = self.folder_path_edit.text().strip()
        elif action_type == "file_open":
            data["path"] = self.file_path_edit.text().strip()
        elif action_type == "url_open":
            data["url"] = self.url_edit.text().strip()
        elif action_type == "app_run":
            data["path"] = self.app_path_edit.text().strip()
        elif action_type == "folder_button":
            data["sub_buttons"] = self._sub_buttons

        return data
