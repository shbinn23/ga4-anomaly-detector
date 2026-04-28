# /main.py (루트)
import uvicorn
import sys
import os

# 현재 경로를 파이썬 패키지 경로에 추가 (보안책)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # "app.main:app"은 app 폴더 내부의 main.py 파일 안에 있는 app 인스턴스를 의미합니다.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)