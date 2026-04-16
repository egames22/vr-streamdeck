"""
버튼 기능 실행 모듈
모든 액션은 별도 스레드에서 실행되어 UI가 멈추지 않음
"""

import os
import webbrowser
import time
import threading
import ctypes
import ctypes.wintypes
import sys
from pathlib import Path

# 디버그 로그
_BASE = Path(os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
             else os.path.dirname(os.path.abspath(__file__)))
_LOG = _BASE / "hotkey_debug.log"

def _log(msg: str):
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ── Windows API ───────────────────────────────────────────────────────────────

_user32 = ctypes.windll.user32

INPUT_KEYBOARD    = 1
KEYEVENTF_KEYUP   = 0x0002
KEYEVENTF_UNICODE = 0x0004


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.wintypes.WORD),
        ("wScan",       ctypes.wintypes.WORD),
        ("dwFlags",     ctypes.wintypes.DWORD),
        ("time",        ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _MOUSEINPUT(ctypes.Structure):
    """union 크기를 Windows 기대값(32바이트)에 맞추기 위해 포함"""
    _fields_ = [
        ("dx",          ctypes.wintypes.LONG),
        ("dy",          ctypes.wintypes.LONG),
        ("mouseData",   ctypes.wintypes.DWORD),
        ("dwFlags",     ctypes.wintypes.DWORD),
        ("time",        ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [
            ("ki", _KEYBDINPUT),
            ("mi", _MOUSEINPUT),   # 이 줄이 union을 32바이트로 만들어 INPUT=40바이트
        ]
    _anonymous_ = ("_i",)
    _fields_ = [("type", ctypes.wintypes.DWORD), ("_i", _I)]


# ── 액션 진입점 ───────────────────────────────────────────────────────────────

def run_action(button_data: dict):
    """버튼 데이터를 받아 해당 액션을 백그라운드 스레드에서 실행"""
    if not button_data:
        return
    action_type = button_data.get("action_type", "")
    handler = ACTION_MAP.get(action_type)
    if handler:
        threading.Thread(target=handler, args=(button_data,), daemon=True).start()


# ── 텍스트 붙여넣기 ───────────────────────────────────────────────────────────

def _paste_text(data: dict):
    """
    버튼 클릭 시 호출.
    WS_EX_NOACTIVATE 덕분에 도크 클릭이 포커스를 빼앗지 않으므로
    직전 포그라운드 창이 그대로 활성 상태 → 클립보드 복사 후 Ctrl+V 전송.
    """
    text   = data.get("text", "")
    method = data.get("paste_method", "clipboard")
    if not text:
        return

    if method == "clipboard":
        _clipboard_and_paste(text)
    else:
        # 타이핑 방식도 SendInput UNICODE 사용 (포커스가 대상 창에 있으므로 동작)
        time.sleep(0.1)
        _send_unicode_text(text)


def _clipboard_and_paste(text: str):
    """클립보드에 복사 후 Ctrl+V 전송"""
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception as e:
        print(f"[actions] 클립보드 복사 실패: {e}")
        return
    time.sleep(0.1)   # 클립보드 쓰기 완료 대기
    _send_ctrl_v()


def paste_for_hotkey(text: str, method: str):
    """
    전역 단축키 발동 시 호출.
    수정자 키(Ctrl/Shift/Alt/Win)를 SendInput으로 즉시 해제한 뒤 붙여넣기한다.
    """
    # 수정자 키 해제 (물리적으로 아직 눌린 상태이므로 합성 key-up 전송)
    for vk in (0x11, 0x10, 0x12, 0x5B):  # Ctrl, Shift, Alt, Win
        inp = _INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = vk
        inp.ki.dwFlags = KEYEVENTF_KEYUP
        arr = (_INPUT * 1)(inp)
        _user32.SendInput(1, arr, ctypes.sizeof(_INPUT))

    time.sleep(0.05)  # 해제 처리 대기

    if method == "clipboard":
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception as e:
            print(f"[actions] 클립보드 복사 실패: {e}")
            return
        time.sleep(0.05)
        _send_ctrl_v()
    else:
        _send_unicode_text(text)


def _send_ctrl_v():
    """SendInput 으로 Ctrl+V 전송"""
    try:
        VK_CTRL = 0x11
        VK_V    = 0x56

        def make_key(vk, flags=0):
            inp = _INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk    = vk
            inp.ki.dwFlags = flags
            return inp

        inputs = [
            make_key(VK_CTRL),
            make_key(VK_V),
            make_key(VK_V,    KEYEVENTF_KEYUP),
            make_key(VK_CTRL, KEYEVENTF_KEYUP),
        ]
        arr = (_INPUT * len(inputs))(*inputs)
        result = _user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))
        _log(f"[paste] SendInput 결과={result} INPUT크기={ctypes.sizeof(_INPUT)}")
    except Exception as e:
        _log(f"[paste] Ctrl+V 오류: {e}")
        print(f"[actions] Ctrl+V 전송 실패: {e}")


def _send_unicode_text(text: str):
    """SendInput KEYEVENTF_UNICODE 로 한글 포함 유니코드 문자열 전송.
    줄바꿈(\\n)은 Enter 키(VK_RETURN)로 전송한다."""
    try:
        VK_RETURN = 0x0D
        BATCH = 40

        def make_unicode_key(ch, flags=0):
            inp = _INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk   = 0
            inp.ki.wScan = ord(ch)
            inp.ki.dwFlags = KEYEVENTF_UNICODE | flags
            return inp

        def make_vk_key(vk, flags=0):
            inp = _INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk   = vk
            inp.ki.dwFlags = flags
            return inp

        chars = list(text)
        i = 0
        while i < len(chars):
            chunk = chars[i:i + BATCH]
            inputs = []
            for ch in chunk:
                if ch == "\n":
                    inputs.append(make_vk_key(VK_RETURN))
                    inputs.append(make_vk_key(VK_RETURN, KEYEVENTF_KEYUP))
                elif ch == "\r":
                    pass  # \r\n 쌍에서 \r 무시
                else:
                    inputs.append(make_unicode_key(ch))
                    inputs.append(make_unicode_key(ch, KEYEVENTF_KEYUP))
            if inputs:
                arr = (_INPUT * len(inputs))(*inputs)
                _user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))
            i += BATCH
            if i < len(chars):
                time.sleep(0.02)
    except Exception as e:
        print(f"[actions] 유니코드 입력 실패: {e}")


# ── 폴더/파일/URL/앱 열기 ────────────────────────────────────────────────────

def _open_folder(data: dict):
    path = os.path.expandvars(os.path.expanduser(data.get("path", "")))
    if path:
        _open_path(path)


def _open_file(data: dict):
    path = os.path.expandvars(os.path.expanduser(data.get("path", "")))
    if path:
        _open_path(path)


def _open_path(path: str):
    try:
        os.startfile(path)
    except Exception as e:
        print(f"[actions] 경로 열기 실패: {path} → {e}")


def _open_url(data: dict):
    url = data.get("url", "").strip()
    if url:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[actions] URL 열기 실패: {e}")


def _run_app(data: dict):
    path = os.path.expandvars(os.path.expanduser(data.get("path", "")))
    if not path:
        return
    try:
        os.startfile(path)
    except Exception as e:
        print(f"[actions] 앱 실행 실패: {path} → {e}")


# ── 키보드 단축키 ─────────────────────────────────────────────────────────────

_VK_MAP = {
    "ctrl": 0x11, "control": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "win": 0x5B, "cmd": 0x5B, "meta": 0x5B,
    "tab": 0x09,
    "enter": 0x0D, "return": 0x0D,
    "esc": 0x1B, "escape": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E, "del": 0x2E,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}


def _run_shortcut(data: dict):
    shortcut_str = data.get("shortcut", "").strip()
    if not shortcut_str:
        return
    try:
        target_hwnd = _user32.GetForegroundWindow()
        parts = [p.strip().lower() for p in shortcut_str.split("+")]
        vk_codes = []
        for part in parts:
            if part in _VK_MAP:
                vk_codes.append(_VK_MAP[part])
            elif len(part) == 1:
                vk = _user32.VkKeyScanA(ctypes.c_char(part.encode("ascii", errors="ignore")))
                if vk != -1:
                    vk_codes.append(vk & 0xFF)
        if not vk_codes:
            return
        if target_hwnd:
            _user32.SetForegroundWindow(target_hwnd)
            time.sleep(0.25)

        def make_key(vk, flags=0):
            inp = _INPUT()
            inp.type = INPUT_KEYBOARD
            inp.ki.wVk    = vk
            inp.ki.dwFlags = flags
            return inp

        key_downs = [make_key(vk) for vk in vk_codes]
        key_ups   = [make_key(vk, KEYEVENTF_KEYUP) for vk in reversed(vk_codes)]
        inputs = key_downs + key_ups
        arr = (_INPUT * len(inputs))(*inputs)
        _user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))
    except Exception as e:
        print(f"[actions] 단축키 실행 실패: {shortcut_str} → {e}")


# ── 액션 맵 ──────────────────────────────────────────────────────────────────

ACTION_MAP = {
    "text_paste":  _paste_text,
    "folder_open": _open_folder,
    "file_open":   _open_file,
    "url_open":    _open_url,
    "app_run":     _run_app,
    "shortcut":    _run_shortcut,
    # folder_button 은 UI 에서 처리
}
