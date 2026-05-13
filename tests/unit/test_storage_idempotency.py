import json
from datetime import date, datetime

import pandas as pd

from app.domain.generic_schemas import GenericAnalysisRequest
from app.infrastructure.json_storage import JSONStorage
from app.services.timeseries_analysis_service import TimeSeriesAnalysisService
from app.services.timeseries_normalizer import TimeSeriesNormalizer


class FakeDetector:
    def train_and_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ds": df["ds"],
                "yhat": [100, 100],
                "yhat_lower": [80, 80],
                "yhat_upper": [120, 120],
            }
        )

    def check_anomaly(self, actual: float, lower: float, upper: float) -> bool:
        return bool(actual < lower or actual > upper)


def make_generic_request(mode="detection", dimensions=None):
    return GenericAnalysisRequest(
        domain="ecommerce",
        mode=mode,
        property_id="prop-1",
        property_name="KR Shop",
        metric_name="eventCount",
        dimensions=dimensions or {},
        series=[
            {"date": "2026-05-01", "value": 100},
            {"date": "2026-05-02", "value": 110},
        ],
    )


def test_json_storage_serializes_date_and_datetime_fields(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"

    storage.save(
        "date-test",
        {
            "day": date(2026, 5, 13),
            "created_at": datetime(2026, 5, 13, 9, 30, 0),
        },
    )

    saved = json.loads(storage.path.read_text(encoding="utf-8"))
    assert saved["date-test"]["day"] == "2026-05-13"
    assert saved["date-test"]["created_at"] == "2026-05-13 09:30:00"


def test_same_analysis_task_generates_same_storage_key():
    first = TimeSeriesNormalizer.from_generic_request(make_generic_request())
    second = TimeSeriesNormalizer.from_generic_request(make_generic_request())

    assert first.analysis_id == second.analysis_id


def test_repeated_generic_analysis_upserts_same_storage_key(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    service = TimeSeriesAnalysisService(detector=FakeDetector(), storage=storage)

    first = service.run_generic_analysis(make_generic_request())
    second = service.run_generic_analysis(make_generic_request())

    generic_path = tmp_path / "generic_analysis_db.json"
    saved = json.loads(generic_path.read_text(encoding="utf-8"))

    assert first["analysis_id"] == second["analysis_id"]
    assert list(saved.keys()) == [first["analysis_id"]]


def test_detection_and_diagnosis_storage_keys_do_not_collide():
    detection = TimeSeriesNormalizer.from_generic_request(
        make_generic_request(mode="detection", dimensions={})
    )
    diagnosis = TimeSeriesNormalizer.from_generic_request(
        make_generic_request(mode="diagnosis", dimensions={})
    )

    assert detection.analysis_id != diagnosis.analysis_id
