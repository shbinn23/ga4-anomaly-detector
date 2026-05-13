import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BASE_DIR / "data" / "results_db.json"
GENERIC_DB_FILE = BASE_DIR / "data" / "generic_analysis_db.json"
CHANNEL_DB_FILE = BASE_DIR / "data" / "channel_anomaly_db.json"


def calculate_point_anomalies(forecast_data: dict) -> list:
    return [
        actual < lower or actual > upper
        for actual, lower, upper in zip(
            forecast_data.get("y", []),
            forecast_data.get("yhat_lower", []),
            forecast_data.get("yhat_upper", []),
        )
    ]


def ensure_forecast_data_contract(result: dict) -> dict:
    if not isinstance(result, dict):
        return result

    forecast_data = result.get("forecast_data")
    if isinstance(forecast_data, dict) and "is_anomaly" not in forecast_data:
        result = dict(result)
        result["forecast_data"] = dict(forecast_data)
        result["forecast_data"]["is_anomaly"] = calculate_point_anomalies(forecast_data)

    return result


def ensure_analysis_data_contract(data: dict) -> dict:
    return {
        key: ensure_forecast_data_contract(value)
        for key, value in data.items()
    }


def load_anomaly_data() -> dict:
    if not DB_FILE.exists():
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return ensure_analysis_data_contract(json.load(f))
    except Exception:
        return {}


def load_generic_analysis_data() -> dict:
    if not GENERIC_DB_FILE.exists():
        return {}
    try:
        with open(GENERIC_DB_FILE, "r", encoding="utf-8") as f:
            return ensure_analysis_data_contract(json.load(f))
    except Exception:
        return {}


def load_channel_analysis_data() -> dict:
    if not CHANNEL_DB_FILE.exists():
        return {}
    try:
        with open(CHANNEL_DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            property_id: ensure_analysis_data_contract(channels)
            for property_id, channels in data.items()
        }
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
