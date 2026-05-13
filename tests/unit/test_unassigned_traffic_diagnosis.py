import pandas as pd

from app.domain.generic_schemas import (
    ThemeDiagnosisResponse,
    UnassignedTrafficDiagnosisRequest,
)
from app.infrastructure.json_storage import JSONStorage
from app.main import app
from app.services.dashboard_results_service import DashboardResultsService
from app.services.timeseries_analysis_service import TimeSeriesAnalysisService
from app.services.timeseries_normalizer import TimeSeriesNormalizer


class SessionsDetector:
    def __init__(self, lower=80, center=100, upper=120):
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


class RatioDetector(SessionsDetector):
    def __init__(self):
        super().__init__(lower=0.05, center=0.1, upper=0.2)


def detection_request(rows, target_date=None):
    from app.domain.generic_schemas import UnassignedTrafficDetectionRequest

    return UnassignedTrafficDetectionRequest(
        property_id="prop-1",
        property_name="KR Shop",
        target_date=target_date,
        rows=rows,
    )


def diagnosis_request(rows, target_date=None, top_n=20, min_total_value=50):
    return UnassignedTrafficDiagnosisRequest(
        property_id="prop-1",
        property_name="KR Shop",
        target_date=target_date,
        top_n=top_n,
        min_total_value=min_total_value,
        rows=rows,
    )


def test_unassigned_diagnosis_accepts_parent_group_key_and_compact_date_format():
    payload = UnassignedTrafficDiagnosisRequest(
        property_id="prop-1",
        property_name="KR Shop",
        target_date="20260502",
        parent_group_key="prop-1:traffic_quality:unassigned_traffic:2026-05-02",
        top_n=20,
        min_total_value=0,
        rows=[
            {"date": "20260501", "sessionSourceMedium": "google / organic", "sessions": 90},
            {"date": "20260502", "sessionSourceMedium": "google / organic", "sessions": 130},
        ],
    )

    tasks = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(payload)

    assert payload.parent_group_key == "prop-1:traffic_quality:unassigned_traffic:2026-05-02"
    assert tasks[0].target_date == "2026-05-02"
    assert [(point.date, point.value) for point in tasks[0].series] == [
        ("2026-05-01", 90.0),
        ("2026-05-02", 130.0),
    ]


def test_unassigned_diagnosis_route_is_registered():
    routes = {
        (route.path, next(iter(route.methods)))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert ("/api/v1/analyze/themes/unassigned-traffic/diagnosis", "POST") in routes


def test_unassigned_diagnosis_rows_split_into_source_medium_tasks():
    tasks = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "google / organic", "sessions": 90},
                {"date": "2026-05-01", "sessionSourceMedium": "direct / none", "sessions": 10},
                {"date": "2026-05-02", "sessionSourceMedium": "google / organic", "sessions": 130},
                {"date": "2026-05-02", "sessionSourceMedium": "direct / none", "sessions": 80},
            ],
            target_date="2026-05-02",
            min_total_value=0,
        )
    )

    by_value = {task.dimensions["dimension_value"]: task for task in tasks}
    assert set(by_value) == {"google / organic", "direct / none"}
    assert by_value["google / organic"].dimensions == {
        "dimension": "sessionSourceMedium",
        "dimension_value": "google / organic",
    }
    assert [(point.date, point.value) for point in by_value["google / organic"].series] == [
        ("2026-05-01", 90.0),
        ("2026-05-02", 130.0),
    ]


def test_unassigned_diagnosis_tasks_pass_only_ds_y_to_detector():
    detector = SessionsDetector()
    service = TimeSeriesAnalysisService(detector=detector)
    payload = diagnosis_request(
        [
            {"date": "2026-05-01", "sessionSourceMedium": "google / organic", "sessions": 90},
            {"date": "2026-05-02", "sessionSourceMedium": "google / organic", "sessions": 130},
        ],
        target_date="2026-05-02",
        min_total_value=0,
    )

    service.run_unassigned_traffic_diagnosis(payload)

    assert len(detector.frames) == 1
    assert list(detector.frames[0].columns) == ["ds", "y"]
    assert detector.frames[0]["y"].tolist() == [90.0, 130.0]


def test_unassigned_diagnosis_keeps_not_set_and_empty_segments():
    tasks = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": None, "sessions": 60},
                {"date": "2026-05-01", "sessionSourceMedium": "", "sessions": 70},
                {"date": "2026-05-02", "sessionSourceMedium": None, "sessions": 60},
                {"date": "2026-05-02", "sessionSourceMedium": "", "sessions": 70},
            ],
            min_total_value=0,
        )
    )

    by_value = {task.dimensions["dimension_value"]: task for task in tasks}
    assert set(by_value) == {"(not set)", "(empty)"}
    assert by_value["(not set)"].metadata["raw_dimension_values"] == [None]
    assert by_value["(empty)"].metadata["raw_dimension_values"] == [""]


def test_unassigned_diagnosis_top_n_and_min_total_value_are_applied():
    rows = []
    for index in range(5):
        rows.extend(
            [
                {
                    "date": "2026-05-01",
                    "sessionSourceMedium": f"segment-{index}",
                    "sessions": 10 + index,
                },
                {
                    "date": "2026-05-02",
                    "sessionSourceMedium": f"segment-{index}",
                    "sessions": 10 + index,
                },
            ]
        )

    tasks = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(
        diagnosis_request(rows, top_n=2, min_total_value=24)
    )

    assert [task.dimensions["dimension_value"] for task in tasks] == [
        "segment-4",
        "segment-3",
    ]


def test_unassigned_diagnosis_min_total_excludes_inactive_low_volume_segments():
    tasks = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "qualified", "sessions": 60},
                {"date": "2026-05-02", "sessionSourceMedium": "qualified", "sessions": 0},
                {"date": "2026-05-01", "sessionSourceMedium": "low-volume", "sessions": 10},
                {"date": "2026-05-02", "sessionSourceMedium": "low-volume", "sessions": 0},
            ],
            target_date="2026-05-02",
            top_n=20,
            min_total_value=50,
        )
    )

    assert [task.dimensions["dimension_value"] for task in tasks] == ["qualified"]


def test_unassigned_diagnosis_keeps_target_date_active_segment_inside_top_n():
    tasks = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "large", "sessions": 100},
                {"date": "2026-05-02", "sessionSourceMedium": "large", "sessions": 0},
                {"date": "2026-05-01", "sessionSourceMedium": "target-active", "sessions": 1},
                {"date": "2026-05-02", "sessionSourceMedium": "target-active", "sessions": 1},
            ],
            target_date="2026-05-02",
            top_n=1,
            min_total_value=50,
        )
    )

    assert [task.dimensions["dimension_value"] for task in tasks] == ["target-active"]


def test_unassigned_diagnosis_target_upper_breach_becomes_alert():
    service = TimeSeriesAnalysisService(detector=SessionsDetector())

    response = service.run_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "google / organic", "sessions": 90},
                {"date": "2026-05-02", "sessionSourceMedium": "google / organic", "sessions": 130},
            ],
            target_date="2026-05-02",
            min_total_value=0,
        )
    )

    item = ThemeDiagnosisResponse(**response).items[0]
    assert item["alert_status"] == "alert"
    assert item["is_current_anomaly"] is True
    assert item["target_point"]["y"] > item["target_point"]["yhat_upper"]


def test_unassigned_diagnosis_lower_breach_is_point_anomaly_not_alert():
    service = TimeSeriesAnalysisService(detector=SessionsDetector())

    response = service.run_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "google / organic", "sessions": 100},
                {"date": "2026-05-02", "sessionSourceMedium": "google / organic", "sessions": 50},
            ],
            target_date="2026-05-02",
            min_total_value=0,
        )
    )

    item = response["items"][0]
    assert item["target_point"]["is_anomaly"] is True
    assert item["target_point"]["y"] < item["target_point"]["yhat_lower"]
    assert item["alert_status"] == "normal"
    assert item["is_current_anomaly"] is False


def test_unassigned_diagnosis_recent_upper_breaches_create_watch():
    service = TimeSeriesAnalysisService(detector=SessionsDetector())

    response = service.run_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "google / organic", "sessions": 130},
                {"date": "2026-05-02", "sessionSourceMedium": "google / organic", "sessions": 125},
                {"date": "2026-05-03", "sessionSourceMedium": "google / organic", "sessions": 100},
            ],
            target_date="2026-05-03",
            min_total_value=0,
        )
    )

    item = response["items"][0]
    assert item["alert_status"] == "watch"
    assert item["is_current_anomaly"] is False
    assert item["recent_anomaly_count"] == 2


def test_unassigned_detection_and_diagnosis_group_key_match_in_dashboard(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"

    detection_service = TimeSeriesAnalysisService(detector=RatioDetector(), storage=storage)
    detection_service.run_unassigned_traffic_detection(
        detection_request(
            [
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Unassigned", "sessions": 10},
                {"date": "2026-05-01", "sessionDefaultChannelGroup": "Organic Search", "sessions": 90},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Unassigned", "sessions": 30},
                {"date": "2026-05-02", "sessionDefaultChannelGroup": "Organic Search", "sessions": 70},
            ],
            target_date="2026-05-02",
        )
    )

    diagnosis_service = TimeSeriesAnalysisService(detector=SessionsDetector(), storage=storage)
    diagnosis_service.run_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "google / organic", "sessions": 90},
                {"date": "2026-05-02", "sessionSourceMedium": "google / organic", "sessions": 130},
            ],
            target_date="2026-05-02",
            min_total_value=0,
        )
    )

    items = DashboardResultsService(storage).list_results()
    group_keys = {item.mode: item.group_key for item in items}
    assert group_keys["detection"] == group_keys["diagnosis"]
    assert group_keys["detection"] == "prop-1:traffic_quality:unassigned_traffic:2026-05-02"


def test_unassigned_diagnosis_metadata_is_preserved():
    task = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(
        diagnosis_request(
            [
                {"date": "2026-05-01", "sessionSourceMedium": "google / organic", "sessions": 90},
                {"date": "2026-05-02", "sessionSourceMedium": "google / organic", "sessions": 130},
            ],
            target_date="2026-05-02",
            top_n=7,
            min_total_value=25,
        )
    )[0]

    assert task.theme_id == "unassigned_traffic"
    assert task.metric_type == "raw_count"
    assert task.alert_direction_policy == "upper_only"
    assert task.metadata["diagnosis_dimension"] == "sessionSourceMedium"
    assert task.metadata["filter"] == "sessionDefaultChannelGroup == Unassigned"
    assert task.metadata["top_n"] == 7
    assert task.metadata["min_total_value"] == 25
    assert task.metadata["target_date"] == "2026-05-02"
    assert task.metadata["parent_theme_id"] == "unassigned_traffic"
