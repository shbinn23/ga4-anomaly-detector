import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BASE_DIR / "data" / "results_db.json"
GENERIC_DB_FILE = BASE_DIR / "data" / "generic_analysis_db.json"


def load_anomaly_data() -> dict:
    if not DB_FILE.exists():
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_generic_analysis_data() -> dict:
    if not GENERIC_DB_FILE.exists():
        return {}
    try:
        with open(GENERIC_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def filter_anomalies(data: dict) -> dict:
    return {k: v for k, v in data.items() if v.get("is_anomaly") is True}


def filter_generic_results(data: dict, domain: str, mode: str) -> dict:
    return {
        k: v
        for k, v in data.items()
        if v.get("domain") == domain and v.get("mode") == mode
    }


def filter_property_results(data: dict, property_id: str) -> dict:
    return {
        k: v
        for k, v in data.items()
        if v.get("property_id") == property_id
    }


def compute_change_rate(result: dict) -> float:
    """실제 세션 vs AI 예측치의 편차율(%). 양수=상승, 음수=하락."""
    actual = result["last_sessions"]
    yhat_list = result["forecast_data"]["yhat"]
    yhat = yhat_list[-1] if yhat_list else 0
    if yhat == 0:
        return 0.0
    return round((actual - yhat) / yhat * 100, 1)


def get_trending(data: dict, n: int = 10) -> list:
    """변화율 절댓값 기준 상위 N개 (Trending Tickers용)."""
    items = [(pid, v, compute_change_rate(v)) for pid, v in data.items()]
    items.sort(key=lambda x: abs(x[2]), reverse=True)
    return items[:n]
