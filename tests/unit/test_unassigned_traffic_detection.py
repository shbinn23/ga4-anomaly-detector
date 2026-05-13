import pandas as pd
import pytest

from app.domain.generic_schemas import GenericAnalysisResponse, UnassignedTrafficDetectionRequest
from app.domain.timeseries import AnalysisTask
from app.infrastructure.json_storage import JSONStorage
from app.main import app
from app.services.dashboard_results_service import DashboardResultsService
from app.services.timeseries_analysis_service import TimeSeriesAnalysisService
from app.services.timeseries_normalizer import TimeSeriesNormalizer


class RatioDetector:
    def __init__(self, lower=0.05, center=0.1, upper=0.2):
        self.lower = lower
        self.center = center
        self.upper = upper
        self.frames = []

    def train_and_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        self.frames.append(df.copy())
        return pd.DataFrame(
            {
                "ds": df["ds"],
                "yhat": [self.center] * len(df),
                "yhat_lower": [self.lower] * len(df),
                "yhat_upper": [self.upper] * len(df),
            }
        )

    def check_anomaly(self, actual: float, lower: float, upper: float) -> bool:
        return bool(actual < lower or actual > upper)


def request(rows, target_date=None):
    return UnassignedTrafficDetectionRequest(
        property_id="prop-1",
        property_name="KR Shop",
        target_date=target_date,
        rows=rows,
    )


def test_unassigned_raw_rows_calculate_total_and_unassigned_sessions():
    task = TimeSeriesNormalizer.from_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 20},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 80},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Paid Search", "sessions": 50},
            ]
        )
    )

    assert task.metadata["total_sessions_by_date"] == {
        "2026-05-01": 100.0,
        "2026-05-02": 50.0,
    }
    assert task.metadata["unassigned_sessions_by_date"] == {"2026-05-01": 20.0}


def test_unassigned_detection_route_is_registered():
    routes = {
        (route.path, next(iter(route.methods)))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert ("/api/v1/analyze/themes/unassigned-traffic/detection", "POST") in routes


def test_unassigned_detection_endpoint_response_exposes_alert_contract(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    service = TimeSeriesAnalysisService(detector=RatioDetector(), storage=storage)
    response = service.run_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 30},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 70},
            ],
            target_date="2026-05-02",
        )
    )

    payload = GenericAnalysisResponse(**response).model_dump(mode="json")
    assert payload["theme_id"] == "unassigned_traffic"
    assert payload["target_date"] == "2026-05-02"
    assert payload["target_point"]["ds"] == "2026-05-02"
    assert payload["alert_status"] == "alert"
    assert payload["is_current_anomaly"] is True
    assert payload["recent_anomaly_count"] == 1
    assert payload["historical_anomaly_count"] == 1
    assert payload["should_run_diagnosis"] is True


def test_unassigned_endpoint_and_dashboard_results_share_alert_status(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    service = TimeSeriesAnalysisService(detector=RatioDetector(), storage=storage)

    response = service.run_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 30},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 70},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 25},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 75},
                {"date": "2026-05-03", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-03", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
            ],
            target_date="2026-05-03",
        )
    )
    item = DashboardResultsService(storage).list_results()[0]

    assert response["alert_status"] == "watch"
    assert response["alert_status"] == item.alert_status
    assert response["is_current_anomaly"] == item.is_current_anomaly
    assert response["recent_anomaly_count"] == item.recent_anomaly_count
    assert response["should_run_diagnosis"] is False


def test_unassigned_session_share_is_derived_ratio_with_zero_total_safe_value():
    task = TimeSeriesNormalizer.from_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 25},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 75},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 0},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Paid Search", "sessions": 0},
            ]
        )
    )

    assert [(point.date, point.value) for point in task.series] == [
        ("2026-05-01", 0.25),
        ("2026-05-02", 0.0),
    ]


def test_unassigned_task_preserves_contract_metadata_and_passes_only_ds_y_to_detector():
    detector = RatioDetector()
    service = TimeSeriesAnalysisService(detector=detector)
    task = TimeSeriesNormalizer.from_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 25},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 75},
            ]
        )
    )

    result = service.run_single_metric_analysis(task)

    assert list(detector.frames[0].columns) == ["ds", "y"]
    assert detector.frames[0]["y"].tolist() == [0.1, 0.25]
    assert result.theme_id == "unassigned_traffic"
    assert result.metric_type == "derived_ratio"
    assert result.alert_direction_policy == "upper_only"
    assert result.metadata["source_dimension"] == "sessionDefaultChannelGroup"
    assert result.metadata["source_metric"] == "sessions"
    assert result.metadata["numerator_filter"] == "sessionDefaultChannelGroup == Unassigned"


def test_unassigned_upper_breach_on_target_date_becomes_current_alert(tmp_path):
    item = run_and_load_dashboard_item(
        tmp_path,
        [
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
            {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 30},
            {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 70},
        ],
        target_date="2026-05-02",
    )

    assert item.alert_status == "alert"
    assert item.is_current_anomaly is True
    assert item.target_point.y > item.target_point.yhat_upper
    assert item.has_anomaly is True


def test_unassigned_endpoint_should_run_diagnosis_only_for_alert(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    service = TimeSeriesAnalysisService(detector=RatioDetector(), storage=storage)

    alert_response = service.run_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 30},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 70},
            ],
            target_date="2026-05-02",
        )
    )
    normal_response = service.run_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
            ],
            target_date="2026-05-02",
        )
    )

    assert alert_response["alert_status"] == "alert"
    assert alert_response["should_run_diagnosis"] is True
    assert normal_response["alert_status"] == "normal"
    assert normal_response["should_run_diagnosis"] is False


def test_unassigned_lower_breach_remains_point_anomaly_not_business_alert(tmp_path):
    item = run_and_load_dashboard_item(
        tmp_path,
        [
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
            {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 100},
        ],
        target_date="2026-05-02",
    )

    assert item.target_point.is_anomaly is True
    assert item.target_point.y < item.target_point.yhat_lower
    assert item.has_anomaly is True
    assert item.alert_status == "normal"
    assert item.is_current_anomaly is False


def test_unassigned_past_anomaly_does_not_create_current_alert(tmp_path):
    item = run_and_load_dashboard_item(
        tmp_path,
        [
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 40},
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 60},
            {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
            {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
        ],
        target_date="2026-05-02",
    )

    assert item.has_anomaly is True
    assert item.alert_status == "normal"
    assert item.is_current_anomaly is False


def test_unassigned_recent_upper_breaches_create_watch_when_target_is_normal(tmp_path):
    item = run_and_load_dashboard_item(
        tmp_path,
        [
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 30},
            {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 70},
            {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 25},
            {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 75},
            {"date": "2026-05-03", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
            {"date": "2026-05-03", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
        ],
        target_date="2026-05-03",
    )

    assert item.target_point.is_anomaly is False
    assert item.alert_status == "watch"
    assert item.is_current_anomaly is False
    assert item.recent_anomaly_count == 2


def test_unassigned_all_zero_derived_ratio_returns_normal_without_detector_call(tmp_path):
    detector = RatioDetector()
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    service = TimeSeriesAnalysisService(detector=detector, storage=storage)

    response = service.run_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 100},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Paid Search", "sessions": 100},
            ],
            target_date="2026-05-02",
        )
    )

    assert detector.frames == []
    assert response["alert_status"] == "normal"
    assert response["is_current_anomaly"] is False
    assert response["should_run_diagnosis"] is False
    assert response["result"]["forecast_data"] == {
        "ds": ["2026-05-01", "2026-05-02"],
        "y": [0.0, 0.0],
        "yhat": [0.0, 0.0],
        "yhat_lower": [0.0, 0.0],
        "yhat_upper": [0.0, 0.0],
        "is_anomaly": [False, False],
    }


def test_unassigned_all_zero_exception_does_not_apply_to_sessions_or_ecommerce():
    service = TimeSeriesAnalysisService(detector=RatioDetector())

    with pytest.raises(ValueError, match="all zero"):
        service.run_single_metric_analysis(
            AnalysisTask(
                analysis_id="prop-1:sessions:detection:sessions:test",
                domain="sessions",
                mode="detection",
                property_id="prop-1",
                property_name=None,
                metric_name="sessions",
                dimensions={},
                series=[
                    {"date": "2026-05-01", "value": 0},
                    {"date": "2026-05-02", "value": 0},
                ],
            )
        )

    with pytest.raises(ValueError, match="all zero"):
        service.run_single_metric_analysis(
            AnalysisTask(
                analysis_id="prop-1:ecommerce:detection:eventCount:test",
                domain="ecommerce",
                mode="detection",
                property_id="prop-1",
                property_name=None,
                metric_name="eventCount",
                dimensions={},
                series=[
                    {"date": "2026-05-01", "value": 0},
                    {"date": "2026-05-02", "value": 0},
                ],
            )
        )


def test_unassigned_storage_key_signature_includes_theme_metric_type_and_policy():
    base = TimeSeriesNormalizer.from_unassigned_traffic_detection(
        request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 20},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 80},
            ]
        )
    )
    different_policy = TimeSeriesNormalizer.build_analysis_id(
        property_id="prop-1",
        property_name="KR Shop",
        corporation=None,
        domain="traffic_quality",
        mode="detection",
        metric_name="unassigned_session_share",
        dimensions={},
        date_start="2026-05-01",
        date_end="2026-05-02",
        filters=base.metadata["filters"],
        aggregation_method="derived_ratio",
        theme_id="unassigned_traffic",
        metric_type="derived_ratio",
        alert_direction_policy="two_sided",
    )

    assert base.analysis_id.startswith("prop-1:traffic_quality:detection:unassigned_session_share:")
    assert base.analysis_id != different_policy
    assert base.metadata["filters"]["numerator_filter"] == "sessionDefaultChannelGroup == Unassigned"

    different_numerator_filter = TimeSeriesNormalizer.build_analysis_id(
        property_id="prop-1",
        property_name="KR Shop",
        corporation=None,
        domain="traffic_quality",
        mode="detection",
        metric_name="unassigned_session_share",
        dimensions={},
        date_start="2026-05-01",
        date_end="2026-05-02",
        filters={
            **base.metadata["filters"],
            "numerator_filter": "sessionDefaultChannelGroup == Direct",
        },
        aggregation_method="derived_ratio",
        theme_id="unassigned_traffic",
        metric_type="derived_ratio",
        alert_direction_policy="upper_only",
    )

    assert base.analysis_id != different_numerator_filter


def run_and_load_dashboard_item(tmp_path, rows, target_date):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    service = TimeSeriesAnalysisService(detector=RatioDetector(), storage=storage)
    service.run_unassigned_traffic_detection(request(rows, target_date=target_date))

    items = DashboardResultsService(storage).list_results()
    assert len(items) == 1
    return items[0]
