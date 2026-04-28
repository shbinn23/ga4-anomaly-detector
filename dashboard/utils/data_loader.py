import json
import os
from pathlib import Path

# 프로젝트 루트 경로 계산 (dashboard/utils/에서 ../../로 이동)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BASE_DIR / "data" / "results_db.json"

def load_anomaly_data() -> dict:
    """분석 결과 JSON 파일을 로드합니다."""
    if not DB_FILE.exists():
        return {}

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def filter_anomalies(data: dict) -> dict:
    """이상치(is_anomaly=True)인 프로퍼티만 필터링합니다."""
    return {k: v for k, v in data.items() if v.get('is_anomaly') is True}