"""
알잘딱버튼 아이콘 생성 스크립트
PyInstaller 빌드 전에 실행: python generate_icon.py

결과물: 알잘딱버튼.ico (256/48/32/16 px 포함)
"""

import sys
import struct
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QByteArray, QBuffer

# 소스 PNG 경로 (이 스크립트와 같은 폴더)
_BASE = os.path.dirname(os.path.abspath(__file__))
SOURCE_PNG = os.path.join(_BASE, "알잘딱버튼 이미지.png")


def load_source_pixmap(size: int) -> QPixmap:
    """소스 PNG를 지정 크기로 리사이즈해서 반환"""
    pm = QPixmap(SOURCE_PNG)
    if pm.isNull():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {SOURCE_PNG}")
    return pm.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def save_ico(pixmap: QPixmap, path: str, sizes=(256, 48, 32, 16)):
    """
    PNG-in-ICO 형식으로 저장 (Windows Vista+, PyInstaller 지원).
    각 크기를 PNG로 압축하여 ICO 컨테이너에 묶음.
    """
    images = []
    for sz in sizes:
        scaled = pixmap.scaled(
            sz, sz,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        img = scaled.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        buf = QByteArray()
        io = QBuffer(buf)
        io.open(QBuffer.OpenModeFlag.WriteOnly)
        img.save(io, "PNG")
        io.close()
        images.append((sz, bytes(buf.data())))

    # ICO 헤더 (reserved=0, type=1, count)
    header = struct.pack("<HHH", 0, 1, len(images))

    dir_offset = 6 + 16 * len(images)
    dir_bytes  = b""
    data_bytes = b""

    for sz, png in images:
        w = h = 0 if sz >= 256 else sz   # 256 → 0 (ICO 스펙)
        entry = struct.pack(
            "<BBBBHHII",
            w, h,            # 폭, 높이
            0, 0,            # 색상 수, 예약
            1, 32,           # 색상 평면, 비트 깊이
            len(png),
            dir_offset + len(data_bytes),
        )
        dir_bytes  += entry
        data_bytes += png

    with open(path, "wb") as f:
        f.write(header + dir_bytes + data_bytes)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pm = load_source_pixmap(512)
    save_ico(pm, os.path.join(_BASE, "알잘딱버튼.ico"))
    print("[OK] 알잘딱버튼.ico 생성 완료 (256/48/32/16 px)")
