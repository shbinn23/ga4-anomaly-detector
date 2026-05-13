from app.domain.schemas import ForecastData
from dashboard.utils.data_loader import ensure_forecast_data_contract


def test_legacy_forecast_data_is_recalculated_for_dashboard_loader():
    result = {
        "forecast_data": {
            "ds": ["2026-05-01", "2026-05-02", "2026-05-03"],
            "y": [100, 70, 150],
            "yhat": [100, 100, 100],
            "yhat_lower": [80, 80, 80],
            "yhat_upper": [120, 120, 120],
        }
    }

    normalized = ensure_forecast_data_contract(result)

    assert normalized["forecast_data"]["is_anomaly"] == [False, True, True]


def test_legacy_forecast_data_is_recalculated_for_api_model():
    forecast_data = ForecastData(
        ds=["2026-05-01", "2026-05-02", "2026-05-03"],
        y=[100, 70, 150],
        yhat=[100, 100, 100],
        yhat_lower=[80, 80, 80],
        yhat_upper=[120, 120, 120],
    )

    assert forecast_data.is_anomaly == [False, True, True]


def test_dashboard_keeps_point_anomaly_calculation_in_data_loader():
    dashboard_source = "dashboard/dashboard.py"
    with open(dashboard_source, "r", encoding="utf-8") as f:
        source = f.read()

    assert "calculate_point_anomalies" not in source
    assert "yhat_lower" not in source
    assert "yhat_upper" not in source
