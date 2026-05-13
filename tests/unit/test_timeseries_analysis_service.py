import pandas as pd

from app.domain.generic_schemas import GenericAnalysisRequest
from app.services.timeseries_analysis_service import TimeSeriesAnalysisService


class FakeDetector:
    def train_and_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ds": df["ds"],
                "yhat": [100, 100, 100],
                "yhat_lower": [80, 80, 80],
                "yhat_upper": [120, 120, 120],
            }
        )

    def check_anomaly(self, actual: float, lower: float, upper: float) -> bool:
        return bool(actual < lower or actual > upper)


def test_generic_analysis_keeps_forecast_data_contract():
    payload = GenericAnalysisRequest(
        domain="ecommerce",
        mode="diagnosis",
        property_id="123",
        metric_name="eventCount",
        dimensions={"eventName": "purchase"},
        series=[
            {"date": "2026-05-01", "value": 100},
            {"date": "2026-05-02", "value": 110},
            {"date": "2026-05-03", "value": 90},
        ],
    )
    service = TimeSeriesAnalysisService(detector=FakeDetector())

    response = service.run_generic_analysis(payload)

    forecast_data = response["result"]["forecast_data"]
    assert list(forecast_data.keys()) == ["ds", "y", "yhat", "yhat_lower", "yhat_upper", "is_anomaly"]
    assert forecast_data["y"] == [100, 110, 90]
    assert forecast_data["is_anomaly"] == [False, False, False]
    assert response["is_anomaly"] is False


def test_detection_anomaly_returns_diagnosis_next_action():
    payload = GenericAnalysisRequest(
        domain="ecommerce",
        mode="detection",
        property_id="123",
        metric_name="eventCount",
        target_events=["view_item", "add_to_cart", "purchase"],
        series=[
            {"date": "2026-05-01", "value": 100},
            {"date": "2026-05-02", "value": 110},
            {"date": "2026-05-03", "value": 150},
        ],
    )
    service = TimeSeriesAnalysisService(detector=FakeDetector())

    response = service.run_generic_analysis(payload)

    assert response["is_anomaly"] is True
    assert response["next_action"] == {
        "type": "request_diagnosis",
        "domain": "ecommerce",
        "property_id": "123",
        "metric_name": "eventCount",
        "dimensions": ["eventName"],
        "target_events": ["view_item", "add_to_cart", "purchase"],
    }
