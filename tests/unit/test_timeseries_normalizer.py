import pytest

from app.domain.generic_schemas import GenericAnalysisRequest
from app.services.timeseries_normalizer import TimeSeriesNormalizer


def test_generic_request_normalizes_to_single_metric_task():
    payload = GenericAnalysisRequest(
        domain="ecommerce",
        mode="detection",
        property_id="123",
        property_name="KR Shop",
        metric_name="eventCount",
        dimensions={"eventName": "purchase", "deviceCategory": "mobile"},
        target_date="2026-05-03",
        series=[
            {"date": "2026-05-01", "value": 100},
            {"date": "2026-05-02", "value": 120},
            {"date": "2026-05-03", "value": 90},
        ],
    )

    task = TimeSeriesNormalizer.from_generic_request(payload)

    assert task.domain == "ecommerce"
    assert task.metric_name == "eventCount"
    assert task.dimensions["eventName"] == "purchase"
    assert task.series[-1].value == 90
    assert task.target_date == "2026-05-03"
    assert task.analysis_id.startswith("123:ecommerce:detection:eventCount:")


def test_generic_request_rejects_mismatched_target_date():
    with pytest.raises(ValueError, match="target_date must match"):
        GenericAnalysisRequest(
            domain="ecommerce",
            property_id="123",
            metric_name="eventCount",
            target_date="2026-05-04",
            series=[
                {"date": "2026-05-01", "value": 100},
                {"date": "2026-05-02", "value": 120},
            ],
        )


def test_normalizer_outputs_prophet_dataframe_shape():
    payload = GenericAnalysisRequest(
        domain="sessions",
        property_id="123",
        metric_name="sessions",
        series=[
            {"date": "2026-05-01", "value": 100},
            {"date": "2026-05-02", "value": 120},
        ],
    )
    task = TimeSeriesNormalizer.from_generic_request(payload)

    df = TimeSeriesNormalizer.to_dataframe(task)

    assert list(df.columns) == ["ds", "y"]
    assert df["y"].tolist() == [100, 120]
