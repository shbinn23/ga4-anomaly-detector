import asyncio

from app.api.routers.management import reset
from app.domain.generic_schemas import GenericAnalysisRequest
from app.domain.schemas import AnomalyRequest, ChannelUpdateTask
from app.domain.timeseries import AnalysisResult
from app.infrastructure.json_storage import JSONStorage
from app.services.anomaly_service import AnomalyService
from app.services.timeseries_analysis_service import TimeSeriesAnalysisService


class NoopDetector:
    pass


class NoopStorage:
    def __init__(self):
        self.saved = {}
        self.batch = {}
        self.channels = {}
        self.generic = {}

    def save(self, key, data):
        self.saved[key] = data

    def save_batch(self, data_map):
        self.batch.update(data_map)

    def save_all_channel_analysis(self, data):
        self.channels.update(data)

    def save_generic_analysis(self, key, data):
        self.generic[key] = data


def fake_result(task):
    return {
        "analysis_id": task.analysis_id,
        "domain": task.domain,
        "mode": task.mode,
        "property_id": task.property_id,
        "property_name": task.property_name,
        "metric_name": task.metric_name,
        "dimensions": task.dimensions,
        "is_anomaly": False,
        "actual_value": task.series[-1].value,
        "lower_bound": 80,
        "upper_bound": 120,
        "target_date": task.target_date or task.series[-1].date,
        "forecast_data": {
            "ds": [item.date for item in task.series],
            "y": [item.value for item in task.series],
            "yhat": [100 for _ in task.series],
            "yhat_lower": [80 for _ in task.series],
            "yhat_upper": [120 for _ in task.series],
            "is_anomaly": [False for _ in task.series],
        },
    }


def patch_common_analysis(monkeypatch, calls):
    def spy(self, task):
        calls.append(task)
        return AnalysisResult(**fake_result(task))

    monkeypatch.setattr(TimeSeriesAnalysisService, "run_single_metric_analysis", spy)


def test_sessions_and_ecommerce_use_common_single_metric_flow(monkeypatch):
    calls = []
    patch_common_analysis(monkeypatch, calls)

    storage = NoopStorage()
    session_service = AnomalyService(detector=NoopDetector(), storage=storage)
    generic_service = TimeSeriesAnalysisService(detector=NoopDetector(), storage=storage)

    session_service.run_analysis(
        AnomalyRequest(
            property_id="session-prop",
            property_name="Session Prop",
            target_date="2026-05-02",
            history_data=[
                {"date": "2026-05-01", "sessions": 100},
                {"date": "2026-05-02", "sessions": 110},
            ],
        )
    )
    session_service.run_channel_analysis(
        ChannelUpdateTask(
            total_count=1,
            data=[
                {
                    "property_id": "session-prop",
                    "property_name": "Session Prop",
                    "grouped_channels": {
                        "Organic Search": [
                            {"date": "2026-05-01", "sessions": 100},
                            {"date": "2026-05-02", "sessions": 110},
                        ]
                    },
                }
            ],
        )
    )
    generic_service.run_generic_analysis(
        GenericAnalysisRequest(
            domain="ecommerce",
            mode="detection",
            property_id="ecommerce-prop",
            metric_name="eventCount",
            series=[
                {"date": "2026-05-01", "value": 100},
                {"date": "2026-05-02", "value": 110},
            ],
        )
    )
    generic_service.run_generic_analysis(
        GenericAnalysisRequest(
            domain="ecommerce",
            mode="diagnosis",
            property_id="ecommerce-prop",
            metric_name="eventCount",
            dimensions={"eventName": "purchase"},
            series=[
                {"date": "2026-05-01", "value": 100},
                {"date": "2026-05-02", "value": 110},
            ],
        )
    )

    assert [(task.domain, task.mode) for task in calls] == [
        ("sessions", "detection"),
        ("sessions", "diagnosis"),
        ("ecommerce", "detection"),
        ("ecommerce", "diagnosis"),
    ]


def test_reset_api_clears_all_analysis_stores(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.path.write_text("{}", encoding="utf-8")
    (tmp_path / "channel_anomaly_db.json").write_text("{}", encoding="utf-8")
    (tmp_path / "generic_analysis_db.json").write_text("{}", encoding="utf-8")

    response = asyncio.run(reset(storage=storage))

    assert sorted(response["cleared_files"]) == [
        "channel_anomaly_db.json",
        "generic_analysis_db.json",
        "results_db.json",
    ]
    assert not storage.path.exists()
    assert not (tmp_path / "channel_anomaly_db.json").exists()
    assert not (tmp_path / "generic_analysis_db.json").exists()
