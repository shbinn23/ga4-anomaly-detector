from datetime import date, timedelta
from typing import Any, Dict, Optional


def summarize_alert_policy(
    forecast_data: Dict[str, Any],
    target_date: Optional[str],
    alert_direction_policy: str = "two_sided",
) -> Dict[str, Any]:
    target_point = target_point_from_forecast(forecast_data, target_date)
    historical_anomaly_count = sum(1 for value in forecast_data.get("is_anomaly", []) if value)
    recent_anomaly_count = recent_breach_count(
        forecast_data,
        target_point,
        alert_direction_policy,
    )
    is_current_anomaly = is_current_alert(target_point, alert_direction_policy)

    if is_current_anomaly:
        alert_status = "alert"
    elif recent_anomaly_count >= 2:
        alert_status = "watch"
    else:
        alert_status = "normal"

    return {
        "target_date": target_point["ds"] if target_point else target_date,
        "target_point": target_point,
        "is_current_anomaly": is_current_anomaly,
        "alert_status": alert_status,
        "historical_anomaly_count": historical_anomaly_count,
        "recent_anomaly_count": recent_anomaly_count,
    }


def target_point_from_forecast(
    forecast_data: Dict[str, Any],
    target_date: Optional[str],
) -> Optional[Dict[str, Any]]:
    dates = forecast_data.get("ds", [])
    if not dates:
        return None

    index = len(dates) - 1
    if target_date in dates:
        index = dates.index(target_date)

    return {
        "ds": dates[index],
        "y": forecast_data["y"][index],
        "yhat": forecast_data["yhat"][index],
        "yhat_lower": forecast_data["yhat_lower"][index],
        "yhat_upper": forecast_data["yhat_upper"][index],
        "is_anomaly": forecast_data["is_anomaly"][index],
    }


def is_current_alert(
    target_point: Optional[Dict[str, Any]],
    alert_direction_policy: str = "two_sided",
) -> bool:
    if not target_point:
        return False
    if alert_direction_policy == "upper_only":
        return target_point["y"] > target_point["yhat_upper"]
    return bool(target_point["is_anomaly"])


def recent_breach_count(
    forecast_data: Dict[str, Any],
    target_point: Optional[Dict[str, Any]],
    alert_direction_policy: str = "two_sided",
) -> int:
    if not target_point or target_point["ds"] not in forecast_data.get("ds", []):
        return 0

    dates = forecast_data["ds"]
    index = dates.index(target_point["ds"])

    try:
        target_day = date.fromisoformat(target_point["ds"])
    except ValueError:
        start = max(0, index - 6)
        return sum(
            1
            for point_index in range(start, index + 1)
            if _is_breach_at_index(forecast_data, point_index, alert_direction_policy)
        )

    start_day = target_day - timedelta(days=6)
    count = 0
    for point_index, point_date in enumerate(dates):
        try:
            current_day = date.fromisoformat(point_date)
        except ValueError:
            continue
        if start_day <= current_day <= target_day and _is_breach_at_index(
            forecast_data,
            point_index,
            alert_direction_policy,
        ):
            count += 1
    return count


def _is_breach_at_index(
    forecast_data: Dict[str, Any],
    index: int,
    alert_direction_policy: str,
) -> bool:
    if alert_direction_policy == "upper_only":
        return forecast_data["y"][index] > forecast_data["yhat_upper"][index]
    return bool(forecast_data["is_anomaly"][index])
