"""
첫 실행 시 보여줄 샘플 버튼 데이터
"""

import os

SAMPLE_PAGES = [
    {
        "id": "page_default",
        "name": "메인",
        "buttons": [
            {
                "id": "btn_1",
                "label": "사용법",
                "icon": "📖",
                "action_type": "text_paste",
                "text": "■ 알잘딱버튼 사용법\n\n[기본 조작]\n• 버튼 클릭 → 지정된 동작 실행\n• 빈 버튼 클릭 → 새 버튼 추가\n• 버튼 우클릭 → 편집 / 삭제\n\n[버튼 기능 종류]\n• 📝 텍스트 붙여넣기 — 문구를 클립보드에 복사 후 자동 붙여넣기\n• 📁 폴더 열기 — 지정 폴더 바로 열기\n• 📄 파일 열기 — 문서·이미지 등 파일 바로 열기\n• 🌐 URL 열기 — 브라우저로 웹페이지 열기\n• 🚀 프로그램 실행 — .exe 파일 바로 실행\n• 📂 폴더형 버튼 — 클릭 시 하위 버튼 팝업\n• ⌨️ 단축키 — 키보드 단축키 실행\n\n[전역 단축키]\n텍스트 붙여넣기 버튼에 단축키를 지정하면\n어떤 창이 열려 있어도 단축키 한 번으로 문구 입력 가능\n\n[화면 배치]\n• 화면 가장자리에 붙이면 자동 숨김\n• 📌 핀 → 항상 표시 고정\n• ⚙ 설정 → 테마·버튼 크기·배열 변경\n• 페이지 추가로 버튼 분류 관리",
                "paste_method": "clipboard"
            },
            {
                "id": "btn_2",
                "label": "바탕화면",
                "icon": "📁",
                "action_type": "folder_open",
                "path": os.path.join(os.path.expanduser("~"), "Desktop")
            },
            {
                "id": "btn_3",
                "label": "메모장",
                "icon": "📄",
                "action_type": "app_run",
                "path": "notepad.exe"
            },
            {
                "id": "btn_4",
                "label": "Google",
                "icon": "🌐",
                "action_type": "url_open",
                "url": "https://www.google.com"
            },
            {
                "id": "btn_5",
                "label": "자주 쓰는 폴더",
                "icon": "📂",
                "action_type": "folder_button",
                "sub_buttons": [
                    {
                        "id": "sub_1",
                        "label": "문서",
                        "icon": "📋",
                        "action_type": "folder_open",
                        "path": os.path.join(os.path.expanduser("~"), "Documents")
                    },
                    {
                        "id": "sub_2",
                        "label": "다운로드",
                        "icon": "⬇️",
                        "action_type": "folder_open",
                        "path": os.path.join(os.path.expanduser("~"), "Downloads")
                    }
                ]
            },
            {
                "id": "btn_6",
                "label": "이모지",
                "icon": "😊",
                "action_type": "emoji_insert"
            }
        ]
    }
]
