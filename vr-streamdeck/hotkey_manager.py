"""
전역 단축키(핫키) 관리 모듈

RegisterHotKey(NULL, ...) 로 메인 스레드 메시지 큐에 등록하고,
QApplication 에 설치된 HotkeyEventFilter 가 WM_HOTKEY 를 수신한다.

사용 예 (dock.py __init__ 안):
    from hotkey_manager import HotkeyManager, HotkeyEventFilter
    from PyQt6.QtWidgets import QApplication

    self._hotkey_manager = HotkeyManager()
    self._hotkey_filter  = HotkeyEventFilter(self._hotkey_manager)
    QApplication.instance().installNativeEventFilter(self._hotkey_filter)
"""

import ctypes
import ctypes.wintypes
import threading
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QAbstractNativeEventFilter

# 로그 파일 경로
_BASE = Path(os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
             else os.path.dirname(os.path.abspath(__file__)))
_LOG = _BASE / "hotkey_debug.log"

def _log(msg: str):
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

_user32   = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

WM_HOTKEY    = 0x0312
MOD_ALT      = 0x0001
MOD_CONTROL  = 0x0002
MOD_SHIFT    = 0x0004
MOD_WIN      = 0x0008
MOD_NOREPEAT = 0x4000


def parse_hotkey(s: str) -> tuple[int, int]:
    """
    단축키 문자열 → (modifiers, vk_code).
    예: 'Ctrl+Shift+1' → (MOD_CONTROL|MOD_SHIFT|MOD_NOREPEAT, 0x31)
    실패 시 (0, 0) 반환.
    '+' 키 자체도 지원: 'Ctrl+Shift++' 처럼 끝이 '++'이면 마지막 키를 '+' 로 처리.
    """
    # '+' 키 자체를 마지막 키로 쓰는 경우 처리 (예: Ctrl+Shift++)
    plus_as_key = False
    if s.endswith("++"):
        plus_as_key = True
        s = s[:-1]   # 마지막 '+' 제거 → 'Ctrl+Shift+'

    parts = [p.strip().lower() for p in s.split("+")]
    modifiers = MOD_NOREPEAT
    vk = 0

    for p in parts:
        if p in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif p == "alt":
            modifiers |= MOD_ALT
        elif p == "shift":
            modifiers |= MOD_SHIFT
        elif p in ("win", "windows", "cmd", "meta"):
            modifiers |= MOD_WIN
        elif p.startswith("f") and p[1:].isdigit():
            n = int(p[1:])
            if 1 <= n <= 12:
                vk = 0x6F + n        # F1=0x70 … F12=0x7B
        elif len(p) == 1:
            if "0" <= p <= "9":
                vk = ord(p)          # '1' → 0x31
            elif p.isalpha():
                vk = ord(p.upper())  # 'a' → 0x41
            else:
                # '*', '@', '#' 등 특수 문자 → VkKeyScanW로 VK 코드 조회
                scan = _user32.VkKeyScanW(ord(p))
                if scan != -1 and (scan & 0xFF) != 0xFF:
                    vk = scan & 0xFF

    # '+' 키 VK 코드 별도 처리 (분할 후엔 빈 문자열이 되어 위 루프에서 처리 불가)
    if plus_as_key:
        scan = _user32.VkKeyScanW(ord('+'))
        if scan != -1 and (scan & 0xFF) != 0xFF:
            vk = scan & 0xFF

    return modifiers, vk


class HotkeyManager:
    """
    RegisterHotKey(NULL, hid, mod, vk) 로 메인 스레드 큐에 단축키를 등록한다.
    반드시 메인(Qt) 스레드에서 register() 를 호출해야 한다.
    """

    def __init__(self):
        self._next_id: int = 3000
        self._callbacks: dict[int, object] = {}     # hid → callable
        self._shortcut_to_hid: dict[str, int] = {}  # shortcut → hid

    # ── 공개 API ──────────────────────────────────────────────────────────────

    def register(self, shortcut: str, callback) -> tuple[bool, str]:
        """
        단축키 등록.
        반환값: (성공여부, 오류메시지)
        성공 시 (True, ""), 실패 시 (False, 사람이 읽을 수 있는 오류메시지)
        """
        mod, vk = parse_hotkey(shortcut)
        if not vk:
            msg = f"[hotkey] 파싱 실패: {shortcut!r}"
            print(msg); _log(msg)
            return False, f"단축키 형식을 인식할 수 없습니다: {shortcut}"

        # 동일 단축키 재등록 시 기존 해제
        if shortcut in self._shortcut_to_hid:
            old = self._shortcut_to_hid.pop(shortcut)
            _user32.UnregisterHotKey(None, old)
            self._callbacks.pop(old, None)

        hid = self._next_id
        self._next_id += 1

        # hwnd=None → 호출 스레드(메인 Qt 스레드)의 메시지 큐에 WM_HOTKEY 게시
        ok = bool(_user32.RegisterHotKey(None, hid, mod, vk))
        if not ok:
            err = _kernel32.GetLastError()
            msg = f"[hotkey] 등록 실패 {shortcut!r} mod={mod:#x} vk={vk:#x} err={err}"
            print(msg); _log(msg)
            if err == 1409:
                return False, f"이미 다른 프로그램이 사용 중인 단축키입니다: {shortcut}"
            return False, f"단축키 등록 실패 (오류코드 {err}): {shortcut}"

        self._callbacks[hid] = callback
        self._shortcut_to_hid[shortcut] = hid
        msg = f"[hotkey] 등록 성공 {shortcut!r} hid={hid} mod={mod:#x} vk={vk:#x}"
        print(msg); _log(msg)
        return True, ""

    def unregister(self, shortcut: str):
        hid = self._shortcut_to_hid.pop(shortcut, None)
        if hid is not None:
            _user32.UnregisterHotKey(None, hid)
            self._callbacks.pop(hid, None)

    def unregister_all(self):
        for hid in list(self._callbacks):
            _user32.UnregisterHotKey(None, hid)
        self._callbacks.clear()
        self._shortcut_to_hid.clear()

    def dispatch(self, hid: int):
        """HotkeyEventFilter 에서 WM_HOTKEY 수신 시 호출"""
        cb = self._callbacks.get(hid)
        if cb:
            threading.Thread(target=cb, daemon=True).start()


class HotkeyEventFilter(QAbstractNativeEventFilter):
    """
    QApplication.installNativeEventFilter() 로 등록.
    메인 스레드 메시지 큐의 WM_HOTKEY 를 가로채 HotkeyManager 에 전달.
    """

    def __init__(self, manager: HotkeyManager):
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, event_type, message):
        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY:
            _log(f"[hotkey] WM_HOTKEY 수신 hid={msg.wParam}")
            self._manager.dispatch(msg.wParam)
        return False, 0
