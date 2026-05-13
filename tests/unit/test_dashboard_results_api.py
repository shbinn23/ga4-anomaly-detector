import asyncio

from fastapi import HTTPException

from app.api.routers.dashboard import dashboard_results
from app.infrastructure.json_storage import JSONStorage
from app.main import app


def _forecast(include_is_anomaly=True):
    data = {
        "ds": ["2026-05-01", "2026-05-02"],
        "y": [100, 150],
        "yhat": [100, 100],
        "yhat_lower": [80, 80],
        "yhat_upper": [120, 120],
    }
    if include_is_anomaly:
        data["is_anomaly"] = [False, True]
    return data


def _forecast_with_dates(dates, anomalies):
    return {
        "ds": dates,
        "y": [150 if anomaly else 100 for anomaly in anomalies],
        "yhat": [100 for _ in dates],
        "yhat_lower": [80 for _ in dates],
        "yhat_upper": [120 for _ in dates],
        "is_anomaly": anomalies,
    }


def test_dashboard_results_get_route_is_registered():
    routes = {
        (route.path, next(iter(route.methods)))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert ("/api/v1/dashboard/results", "GET") in routes


def test_dashboard_results_returns_empty_items_for_empty_storage(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"

    response = asyncio.run(dashboard_results(storage=storage))

    assert response.model_dump(mode="json") == {"items": []}


def test_dashboard_results_returns_generic_analysis_result(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save_generic_analysis(
        "generic-key",
        {
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "detection",
            "property_id": "prop-1",
            "property_name": "Store",
            "theme_id": None,
            "metric_name": "eventCount",
            "metric_type": None,
            "alert_direction_policy": "two_sided",
            "dimension": None,
            "dimension_value": None,
            "dimensions": {},
            "metadata": {},
            "has_anomaly": True,
            "is_anomaly": True,
            "actual_value": 150,
            "lower_bound": 80,
            "upper_bound": 120,
            "target_date": "2026-05-02",
            "forecast_data": _forecast(),
        },
    )

    response = asyncio.run(dashboard_results(storage=storage))

    assert response.model_dump(mode="json")["items"] == [
        {
            "id": "generic-key",
            "source": "generic_analysis_db",
            "group_key": "prop-1:ecommerce:eventCount:2026-05-02",
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "detection",
            "property_id": "prop-1",
            "property_name": "Store",
            "theme_id": None,
            "metric_name": "eventCount",
            "metric_type": None,
            "alert_direction_policy": "two_sided",
            "dimension": None,
            "dimension_value": None,
            "dimensions": {},
            "metadata": {},
            "has_anomaly": True,
            "is_anomaly": True,
            "actual_value": 150.0,
            "lower_bound": 80.0,
            "upper_bound": 120.0,
            "target_date": "2026-05-02",
            "target_point": {
                "ds": "2026-05-02",
                "y": 150.0,
                "yhat": 100.0,
                "yhat_lower": 80.0,
                "yhat_upper": 120.0,
                "is_anomaly": True,
            },
            "is_current_anomaly": True,
            "alert_status": "alert",
            "historical_anomaly_count": 1,
            "recent_anomaly_count": 1,
            "latest_point": {
                "ds": "2026-05-02",
                "y": 150.0,
                "yhat": 100.0,
                "yhat_lower": 80.0,
                "yhat_upper": 120.0,
                "is_anomaly": True,
            },
            "forecast_data": _forecast(),
        }
    ]


def test_dashboard_results_recomputes_legacy_missing_point_anomalies(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save(
        "legacy-prop",
        {
            "property_name": "Legacy Property",
            "is_anomaly": True,
            "last_sessions": 150,
            "updated_at": "2026-05-02",
            "forecast_data": _forecast(include_is_anomaly=False),
        },
    )

    response = asyncio.run(dashboard_results(storage=storage))

    item = response.model_dump(mode="json")["items"][0]
    assert item["forecast_data"]["is_anomaly"] == [False, True]
    assert item["has_anomaly"] is True
    assert item["is_current_anomaly"] is True
    assert item["alert_status"] == "alert"
    assert item["dimension"] is None
    assert item["dimension_value"] is None
    assert set(item["forecast_data"]) == {
        "ds",
        "y",
        "yhat",
        "yhat_lower",
        "yhat_upper",
        "is_anomaly",
    }


def test_dashboard_results_has_anomaly_comes_from_forecast_points(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save(
        "legacy-prop",
        {
            "property_name": "Legacy Property",
            "is_anomaly": False,
            "last_sessions": 150,
            "updated_at": "2026-05-02",
            "forecast_data": _forecast(),
        },
    )

    response = asyncio.run(dashboard_results(storage=storage))
    item = response.model_dump(mode="json")["items"][0]

    assert item["is_anomaly"] is False
    assert item["has_anomaly"] is True


def test_dashboard_current_anomaly_uses_target_date_not_past_points(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save_generic_analysis(
        "generic-key",
        {
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "detection",
            "property_id": "prop-1",
            "property_name": "Store",
            "metric_name": "eventCount",
            "dimensions": {},
            "is_anomaly": False,
            "actual_value": 100,
            "lower_bound": 80,
            "upper_bound": 120,
            "target_date": "2026-05-04",
            "forecast_data": _forecast_with_dates(
                ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"],
                [True, False, False, False],
            ),
        },
    )

    item = asyncio.run(dashboard_results(storage=storage)).model_dump(mode="json")["items"][0]

    assert item["has_anomaly"] is True
    assert item["is_current_anomaly"] is False
    assert item["alert_status"] == "normal"


def test_dashboard_alert_status_alert_when_target_date_is_anomaly(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save_generic_analysis(
        "generic-key",
        {
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "detection",
            "property_id": "prop-1",
            "property_name": "Store",
            "metric_name": "eventCount",
            "dimensions": {},
            "is_anomaly": True,
            "actual_value": 150,
            "lower_bound": 80,
            "upper_bound": 120,
            "target_date": "2026-05-04",
            "forecast_data": _forecast_with_dates(
                ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"],
                [False, False, False, True],
            ),
        },
    )

    item = asyncio.run(dashboard_results(storage=storage)).model_dump(mode="json")["items"][0]

    assert item["target_point"]["ds"] == "2026-05-04"
    assert item["is_current_anomaly"] is True
    assert item["alert_status"] == "alert"


def test_dashboard_alert_status_watch_for_recent_repeated_anomalies(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save_generic_analysis(
        "generic-key",
        {
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "detection",
            "property_id": "prop-1",
            "property_name": "Store",
            "metric_name": "eventCount",
            "dimensions": {},
            "is_anomaly": False,
            "actual_value": 100,
            "lower_bound": 80,
            "upper_bound": 120,
            "target_date": "2026-05-08",
            "forecast_data": _forecast_with_dates(
                [
                    "2026-05-01",
                    "2026-05-02",
                    "2026-05-03",
                    "2026-05-04",
                    "2026-05-05",
                    "2026-05-06",
                    "2026-05-07",
                    "2026-05-08",
                ],
                [False, True, False, False, True, False, False, False],
            ),
        },
    )

    item = asyncio.run(dashboard_results(storage=storage)).model_dump(mode="json")["items"][0]

    assert item["is_current_anomaly"] is False
    assert item["recent_anomaly_count"] == 2
    assert item["alert_status"] == "watch"


def test_dashboard_alert_status_normal_when_recent_anomalies_are_insufficient(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save_generic_analysis(
        "generic-key",
        {
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "detection",
            "property_id": "prop-1",
            "property_name": "Store",
            "metric_name": "eventCount",
            "dimensions": {},
            "is_anomaly": False,
            "actual_value": 100,
            "lower_bound": 80,
            "upper_bound": 120,
            "target_date": "2026-05-08",
            "forecast_data": _forecast_with_dates(
                [
                    "2026-05-01",
                    "2026-05-02",
                    "2026-05-03",
                    "2026-05-04",
                    "2026-05-05",
                    "2026-05-06",
                    "2026-05-07",
                    "2026-05-08",
                ],
                [True, False, False, False, False, False, False, False],
            ),
        },
    )

    item = asyncio.run(dashboard_results(storage=storage)).model_dump(mode="json")["items"][0]

    assert item["has_anomaly"] is True
    assert item["recent_anomaly_count"] == 0
    assert item["alert_status"] == "normal"


def test_dashboard_group_key_uses_effective_target_date(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save_generic_analysis(
        "generic-key",
        {
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "detection",
            "property_id": "prop-1",
            "property_name": "Store",
            "metric_name": "eventCount",
            "dimensions": {},
            "is_anomaly": False,
            "actual_value": 100,
            "lower_bound": 80,
            "upper_bound": 120,
            "target_date": "2026-05-99",
            "forecast_data": _forecast_with_dates(
                ["2026-05-01", "2026-05-02"],
                [False, False],
            ),
        },
    )

    item = asyncio.run(dashboard_results(storage=storage)).model_dump(mode="json")["items"][0]

    assert item["target_date"] == "2026-05-02"
    assert item["target_point"]["ds"] == "2026-05-02"
    assert item["group_key"] == "prop-1:ecommerce:eventCount:2026-05-02"


def test_dashboard_results_diagnosis_item_exposes_dimension_fields(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.save_generic_analysis(
        "diagnosis-key",
        {
            "analysis_id": "analysis-1",
            "domain": "ecommerce",
            "mode": "diagnosis",
            "property_id": "prop-1",
            "property_name": "Store",
            "metric_name": "eventCount",
            "dimensions": {"eventName": "purchase"},
            "is_anomaly": True,
            "actual_value": 150,
            "lower_bound": 80,
            "upper_bound": 120,
            "target_date": "2026-05-02",
            "forecast_data": _forecast(),
        },
    )

    response = asyncio.run(dashboard_results(storage=storage))
    item = response.model_dump(mode="json")["items"][0]

    assert item["dimension"] == "eventName"
    assert item["dimension_value"] == "purchase"
    assert item["group_key"] == "prop-1:ecommerce:eventCount:2026-05-02"
    assert item["target_point"] == {
        "ds": "2026-05-02",
        "y": 150.0,
        "yhat": 100.0,
        "yhat_lower": 80.0,
        "yhat_upper": 120.0,
        "is_anomaly": True,
    }
    assert item["is_current_anomaly"] is True
    assert item["alert_status"] == "alert"
    assert item["latest_point"] == {
        "ds": "2026-05-02",
        "y": 150.0,
        "yhat": 100.0,
        "yhat_lower": 80.0,
        "yhat_upper": 120.0,
        "is_anomaly": True,
    }


def test_dashboard_results_does_not_hide_broken_json(tmp_path):
    storage = JSONStorage()
    storage.path = tmp_path / "results_db.json"
    storage.path.write_text("{broken", encoding="utf-8")

    try:
        asyncio.run(dashboard_results(storage=storage))
    except HTTPException as exc:
        assert exc.status_code == 500
        assert "Failed to read dashboard store results_db.json" in exc.detail
    else:
        raise AssertionError("Broken JSON should raise HTTPException")
