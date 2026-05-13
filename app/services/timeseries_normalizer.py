import hashlib
import json
from typing import Any, Dict

import pandas as pd

from ..domain.generic_schemas import GenericAnalysisRequest
from ..domain.timeseries import TimeSeriesTask, TimeSeriesValue


class TimeSeriesNormalizer:
    """Converts domain-specific payloads into canonical single-metric tasks."""

    @staticmethod
    def from_generic_request(payload: GenericAnalysisRequest) -> TimeSeriesTask:
        dimensions = dict(payload.dimensions)
        series = [
            TimeSeriesValue(date=item.date.isoformat(), value=item.value)
            for item in payload.series
        ]

        return TimeSeriesTask(
            analysis_id=TimeSeriesNormalizer.build_analysis_id(
                property_id=payload.property_id,
                domain=payload.domain,
                metric_name=payload.metric_name,
                dimensions=dimensions,
            ),
            domain=payload.domain,
            mode=payload.mode,
            property_id=payload.property_id,
            property_name=payload.property_name,
            metric_name=payload.metric_name,
            dimensions=dimensions,
            series=series,
            target_date=payload.target_date.isoformat() if payload.target_date else series[-1].date,
            metadata={"target_events": payload.target_events or []},
        )

    @staticmethod
    def to_dataframe(task: TimeSeriesTask) -> pd.DataFrame:
        df = pd.DataFrame(
            [{"ds": item.date, "y": item.value} for item in task.series]
        )
        df["ds"] = pd.to_datetime(df["ds"])
        return df

    @staticmethod
    def build_analysis_id(
        property_id: str,
        domain: str,
        metric_name: str,
        dimensions: Dict[str, Any],
    ) -> str:
        encoded_dimensions = json.dumps(dimensions, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha1(encoded_dimensions.encode("utf-8")).hexdigest()[:12]
        return f"{property_id}:{domain}:{metric_name}:{digest}"
