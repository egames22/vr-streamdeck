"""
config.json / pages.json 읽기/쓰기 관리
"""

import json
import os
import sys
from pathlib import Path
from copy import deepcopy
from sample_data import SAMPLE_PAGES

BASE_DIR = Path(os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))

SETTINGS_DIR = BASE_DIR / "알잘딱버튼_설정"
CONFIG_FILE = SETTINGS_DIR / "config.json"
PAGES_FILE = SETTINGS_DIR / "pages.json"
IMAGES_DIR = SETTINGS_DIR / "images"

DEFAULT_CONFIG = {
    "theme": {
        "background": "#1e1e2e",
        "button_color": "#313244",
        "button_hover": "#45475a",
        "button_pressed": "#181825",
        "text_color": "#cdd6f4",
        "accent_color": "#89b4fa",
        "border_color": "#585b70"
    },
    "opacity": 0.92,
    "grid": {"cols": 3, "rows": 2},
    "label_mode": "always",
    "pinned": False,
    "position": {"x": -1, "y": -1},
    "snapped": None,
    "autostart": False,
    "button_size": 64,
    "icon_font_size": 28,
    "label_font_size": 9
}


class ConfigManager:
    def __init__(self):
        self._config = {}
        self._pages = []
        self._ensure_dirs()
        self._load()

    # ── 내부 초기화 ──────────────────────────────────────────────────────────

    def _ensure_dirs(self):
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self):
        # config.json
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._config = self._merge(DEFAULT_CONFIG, loaded)
            except Exception:
                self._config = deepcopy(DEFAULT_CONFIG)
        else:
            self._config = deepcopy(DEFAULT_CONFIG)
            self.save_config()

        # pages.json
        if PAGES_FILE.exists():
            try:
                with open(PAGES_FILE, "r", encoding="utf-8") as f:
                    self._pages = json.load(f)
                if self._migrate_pages():
                    self.save_pages()
            except Exception:
                self._pages = deepcopy(SAMPLE_PAGES)
        else:
            self._pages = deepcopy(SAMPLE_PAGES)
            self.save_pages()

    def _migrate_pages(self) -> bool:
        """저장된 pages.json에 구버전 데이터가 있을 때 자동 수정. 변경 시 True 반환."""
        changed = False
        for page in self._pages:
            for btn in page.get("buttons", []):
                if btn and btn.get("action_type") == "shortcut" and btn.get("shortcut") == "Win+.":
                    btn["action_type"] = "emoji_insert"
                    btn.pop("shortcut", None)
                    changed = True
        return changed

    def _merge(self, default: dict, override: dict) -> dict:
        """default를 기반으로 override 값을 덮어씌운 새 dict 반환"""
        result = deepcopy(default)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge(result[k], v)
            else:
                result[k] = v
        return result

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def pages(self):
        return self._pages

    def get(self, key: str, default=None):
        """
        점(.) 표기 지원: config.get("grid.cols", 3)
        """
        parts = key.split(".")
        val = self._config
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default
        return val

    def set(self, key: str, value):
        parts = key.split(".")
        target = self._config
        for p in parts[:-1]:
            target = target.setdefault(p, {})
        target[parts[-1]] = value

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ConfigManager] config 저장 실패: {e}")

    def save_pages(self):
        try:
            with open(PAGES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._pages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ConfigManager] pages 저장 실패: {e}")

    def export_config(self, dest_path: str):
        """설정 파일 전체를 지정 경로로 내보내기"""
        try:
            data = {
                "config": self._config,
                "pages": self._pages
            }
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ConfigManager] export 실패: {e}")
            return False

    def import_config(self, src_path: str):
        """내보낸 설정 파일 불러오기"""
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._config = self._merge(DEFAULT_CONFIG, data.get("config", {}))
            self._pages = data.get("pages", deepcopy(SAMPLE_PAGES))
            self.save_config()
            self.save_pages()
            return True
        except Exception as e:
            print(f"[ConfigManager] import 실패: {e}")
            return False
