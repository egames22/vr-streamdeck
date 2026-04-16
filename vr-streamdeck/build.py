"""
알잘딱버튼 빌드 스크립트
사용법: python build.py
"""
import os
import sys
import subprocess
from pathlib import Path

PYTHON = sys.executable
BASE   = Path(__file__).parent


def run(cmd):
    print(">", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[FAIL] 빌드 실패 - 위 오류를 확인하세요.")
        sys.exit(result.returncode)


def step(n, total, msg):
    print(f"\n[{n}/{total}] {msg}")


total = 4

step(1, total, "패키지 설치")
run([PYTHON, "-m", "pip", "install", "-r", str(BASE / "requirements.txt")])

step(2, total, "아이콘 생성")
run([PYTHON, str(BASE / "generate_icon.py")])

step(3, total, "설정 폴더 준비")
settings_dir = BASE / "알잘딱버튼_설정"
settings_dir.mkdir(exist_ok=True)
print(f"  폴더 확인: {settings_dir}")

step(4, total, "PyInstaller 빌드")
png_src   = BASE / "알잘딱버튼 이미지.png"
logo1_src = BASE / "논산여상 로고.png"
logo2_src = BASE / "갓쌤에듀 로고.png"
run([
    PYTHON, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "알잘딱버튼",
    "--icon", str(BASE / "알잘딱버튼.ico"),
    "--add-data", f"{settings_dir}{os.pathsep}알잘딱버튼_설정",
    "--add-data", f"{png_src}{os.pathsep}.",
    "--add-data", f"{logo1_src}{os.pathsep}.",
    "--add-data", f"{logo2_src}{os.pathsep}.",
    "--hidden-import", "pynput.keyboard._win32",
    "--hidden-import", "pynput.mouse._win32",
    str(BASE / "main.py"),
])

print("\n[완료] dist/알잘딱버튼.exe 생성됨")
