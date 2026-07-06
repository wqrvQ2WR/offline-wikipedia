#!/bin/bash
cd "$(dirname "$0")"
echo "오프라인 위키디피아 관리 앱을 시작합니다..."
echo "종료하려면 이 창에서 Ctrl+C 를 누르세요."
exec /usr/bin/python3 app.py --open
