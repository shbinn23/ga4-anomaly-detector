import pandas as pd
import pytest

from app.domain.generic_schemas import GenericAnalysisRequest
from app.domain.timeseries import AnalysisResult, AnalysisTask
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


class ExplodingDetector:
    def train_and_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        raise AssertionError("Prophet should not be called")

    def check_anomaly(self, actual: float, lower: float, upper: float) -> bool:
        raise AssertionError("Anomaly check should not be called")


class BadBoundsDetector(FakeDetector):
    def train_and_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ds": df["ds"],
                "yhat": [100, 100, 100],
                "yhat_lower": [120, 120, 120],
                "yhat_upper": [80, 80, 80],
            }
        )


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


def test_analysis_result_fills_legacy_missing_point_anomalies():
    result = AnalysisResult(
        analysis_id="123:ecommerce:eventCount:test",
        domain="ecommerce",
        mode="diagnosis",
        property_id="123",
        property_name="KR Shop",
        metric_name="eventCount",
        dimensions={"eventName": "purchase"},
        is_anomaly=True,
        actual_value=150,
        lower_bound=80,
        upper_bound=120,
        target_date="2026-05-03",
        forecast_data={
            "ds": ["2026-05-01", "2026-05-02", "2026-05-03"],
            "y": [100, 70, 150],
            "yhat": [100, 100, 100],
            "yhat_lower": [80, 80, 80],
            "yhat_upper": [120, 120, 120],
        },
    )

    assert result.forecast_data["is_anomaly"] == [False, True, True]


def test_detection_and_diagnosis_share_analysis_result_shape():
    service = TimeSeriesAnalysisService(detector=FakeDetector())
    base_series = [
        {"date": "2026-05-01", "value": 100},
        {"date": "2026-05-02", "value": 110},
        {"date": "2026-05-03", "value": 90},
    ]
    detection = service.run_single_metric_analysis(
        AnalysisTask(
            analysis_id="123:ecommerce:eventCount:detection",
            domain="ecommerce",
            mode="detection",
            property_id="123",
            property_name="KR Shop",
            metric_name="eventCount",
            dimensions={},
            series=base_series,
        )
    )
    diagnosis = service.run_single_metric_analysis(
        AnalysisTask(
            analysis_id="123:ecommerce:eventCount:diagnosis",
            domain="ecommerce",
            mode="diagnosis",
            property_id="123",
            property_name="KR Shop",
            metric_name="eventCount",
            dimensions={"eventName": "purchase"},
            series=base_series,
        )
    )

    assert set(detection.model_dump().keys()) == set(diagnosis.model_dump().keys())
    assert set(detection.forecast_data.keys()) == set(diagnosis.forecast_data.keys())


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


def test_nan_or_inf_values_are_blocked_before_detector():
    service = TimeSeriesAnalysisService(detector=ExplodingDetector())

    for bad_value in [float("nan"), float("inf"), float("-inf")]:
        with pytest.raises(ValueError, match="finite"):
            service.run_single_metric_analysis(
                AnalysisTask(
                    analysis_id="bad",
                    domain="generic",
                    mode="detection",
                    property_id="prop",
                    property_name=None,
                    metric_name="metric",
                    dimensions={},
                    series=[
                        {"date": "2026-05-01", "value": 100},
                        {"date": "2026-05-02", "value": bad_value},
                    ],
                )
            )


def test_duplicate_or_missing_ds_is_blocked_before_detector():
    service = TimeSeriesAnalysisService(detector=ExplodingDetector())

    with pytest.raises(ValueError, match="duplicate ds"):
        service.run_single_metric_analysis(
            AnalysisTask(
                analysis_id="duplicate",
                domain="generic",
                mode="detection",
                property_id="prop",
                property_name=None,
                metric_name="metric",
                dimensions={},
                series=[
                    {"date": "2026-05-01", "value": 100},
                    {"date": "2026-05-01", "value": 110},
                ],
            )
        )

    with pytest.raises(ValueError, match="missing ds"):
        service.run_single_metric_analysis(
            AnalysisTask(
                analysis_id="missing",
                domain="generic",
                mode="detection",
                property_id="prop",
                property_name=None,
                metric_name="metric",
                dimensions={},
                series=[
                    {"date": "2026-05-01", "value": 100},
                    {"date": "", "value": 110},
                ],
            )
        )


def test_insufficient_or_all_zero_series_is_blocked_before_detector():
    service = TimeSeriesAnalysisService(detector=ExplodingDetector())

    with pytest.raises(Exception):
        AnalysisTask(
            analysis_id="short",
            domain="generic",
            mode="detection",
            property_id="prop",
            property_name=None,
            metric_name="metric",
            dimensions={},
            series=[
                {"date": "2026-05-01", "value": 100},
            ],
        )

    with pytest.raises(ValueError, match="all zero"):
        service.run_single_metric_analysis(
            AnalysisTask(
                analysis_id="zero",
                domain="generic",
                mode="detection",
                property_id="prop",
                property_name=None,
                metric_name="metric",
                dimensions={},
                series=[
                    {"date": "2026-05-01", "value": 0},
                    {"date": "2026-05-02", "value": 0},
                ],
            )
        )


def test_invalid_forecast_bounds_are_blocked():
    service = TimeSeriesAnalysisService(detector=BadBoundsDetector())

    with pytest.raises(ValueError, match="Forecast bounds"):
        service.run_single_metric_analysis(
            AnalysisTask(
                analysis_id="bad-forecast",
                domain="generic",
                mode="detection",
                property_id="prop",
                property_name=None,
                metric_name="metric",
                dimensions={},
                series=[
                    {"date": "2026-05-01", "value": 100},
                    {"date": "2026-05-02", "value": 110},
                    {"date": "2026-05-03", "value": 120},
                ],
            )
        )
