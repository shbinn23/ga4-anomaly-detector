import json
import os
from datetime import date, datetime

import pandas as pd
import pytest

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


def make_generic_request(mode="detection", dimensions=None, filters=None):
    return GenericAnalysisRequest(
        domain="ecommerce",
        mode=mode,
        property_id="prop-1",
        property_name="KR Shop",
        metric_name="eventCount",
        dimensions=dimensions or {},
        filters=filters or {"eventName": ["view_item", "purchase"]},
        aggregation_method="sum",
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
    assert saved["date-test"]["created_at"] == "2026-05-13T09:30:00"


def test_json_storage_rejects_unexpected_object_types(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"

    with pytest.raises(Exception, match="not JSON serializable"):
        storage.save("object-test", {"bad": object()})


def test_same_analysis_task_generates_same_storage_key():
    first = TimeSeriesNormalizer.from_generic_request(make_generic_request())
    second = TimeSeriesNormalizer.from_generic_request(make_generic_request())

    assert first.analysis_id == second.analysis_id


def test_date_range_changes_storage_key():
    base = TimeSeriesNormalizer.from_generic_request(make_generic_request())
    changed = TimeSeriesNormalizer.from_generic_request(
        GenericAnalysisRequest(
            domain="ecommerce",
            mode="detection",
            property_id="prop-1",
            property_name="KR Shop",
            metric_name="eventCount",
            filters={"eventName": ["view_item", "purchase"]},
            aggregation_method="sum",
            series=[
                {"date": "2026-05-02", "value": 100},
                {"date": "2026-05-03", "value": 110},
            ],
        )
    )

    assert base.analysis_id != changed.analysis_id


def test_filters_change_storage_key():
    base = TimeSeriesNormalizer.from_generic_request(make_generic_request())
    changed = TimeSeriesNormalizer.from_generic_request(
        make_generic_request(filters={"eventName": ["purchase"]})
    )

    assert base.analysis_id != changed.analysis_id


def test_dimension_value_changes_storage_key():
    first = TimeSeriesNormalizer.from_generic_request(
        make_generic_request(dimensions={"eventName": "purchase"})
    )
    second = TimeSeriesNormalizer.from_generic_request(
        make_generic_request(dimensions={"eventName": "add_to_cart"})
    )

    assert first.analysis_id != second.analysis_id


def test_aggregation_method_changes_storage_key():
    base = TimeSeriesNormalizer.from_generic_request(make_generic_request())
    changed = TimeSeriesNormalizer.from_generic_request(
        GenericAnalysisRequest(
            domain="ecommerce",
            mode="detection",
            property_id="prop-1",
            property_name="KR Shop",
            metric_name="eventCount",
            filters={"eventName": ["view_item", "purchase"]},
            aggregation_method="avg",
            series=[
                {"date": "2026-05-01", "value": 100},
                {"date": "2026-05-02", "value": 110},
            ],
        )
    )

    assert base.analysis_id != changed.analysis_id


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


def test_json_storage_atomic_write_path(tmp_path, monkeypatch):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    calls = []

    original_replace = os.replace

    def spy_replace(src, dst):
        calls.append((src, dst))
        original_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy_replace)

    storage.save("atomic-test", {"value": 1})

    assert calls
    assert calls[-1][1] == storage.path
    assert json.loads(storage.path.read_text(encoding="utf-8")) == {
        "atomic-test": {"value": 1}
    }


def test_reset_uses_safe_write_path(tmp_path, monkeypatch):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    calls = []

    def spy_write(path, data):
        calls.append((path.name, data))
        JSONStorage._write_json(storage, path, data)

    monkeypatch.setattr(storage, "_write_json", spy_write)

    cleared = storage.clear_all_analysis_files()

    assert sorted(cleared) == [
        "channel_anomaly_db.json",
        "generic_analysis_db.json",
        "results_db.json",
    ]
    assert sorted(name for name, _ in calls) == sorted(cleared)
    assert all(data == {} for _, data in calls)
