from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "GA4 Anomaly Detector"

    # 경로 설정 (절대 경로 보장)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    REPORT_DIR: Path = BASE_DIR / "static" / "reports"

    # DB 파일명
    DB_FILE_NAME: str = "results_db.json"

    # ML 파라미터 (Phase 3 확장을 고려하여 중앙 관리)
    PROPHET_INTERVAL_WIDTH: float = 0.80

    class Config:
        env_file = ".env"

settings = Settings()

# 필요한 디렉토리 자동 생성
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)