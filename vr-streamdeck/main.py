"""
알잘딱버튼 — 진입점
"""

import sys
import os

# 실행 파일(.exe) 기준으로 작업 디렉터리 설정
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from config_manager import ConfigManager
from dock import DockWindow


def main():
    # High DPI 지원
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("알잘딱버튼")
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager()
    dock = DockWindow(config)
    dock.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
