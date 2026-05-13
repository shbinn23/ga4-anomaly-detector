import hashlib
import json
from typing import Any, Dict

import pandas as pd

from ..domain.generic_schemas import GenericAnalysisRequest
from ..domain.timeseries import AnalysisTask, TimeSeriesPoint


class TimeSeriesNormalizer:
    """Converts domain-specific payloads into canonical single-metric tasks."""

    @staticmethod
    def from_generic_request(payload: GenericAnalysisRequest) -> AnalysisTask:
        dimensions = dict(payload.dimensions)
        filters = dict(payload.filters)
        if payload.target_events:
            filters["target_events"] = payload.target_events
        series = [
            TimeSeriesPoint(date=item.date.isoformat(), value=item.value)
            for item in payload.series
        ]
        date_start = payload.date_start.isoformat() if payload.date_start else series[0].date
        date_end = payload.date_end.isoformat() if payload.date_end else series[-1].date

        return AnalysisTask(
            analysis_id=TimeSeriesNormalizer.build_analysis_id(
                property_id=payload.property_id,
                property_name=payload.property_name,
                corporation=payload.corporation,
                domain=payload.domain,
                mode=payload.mode,
                metric_name=payload.metric_name,
                dimensions=dimensions,
                date_start=date_start,
                date_end=date_end,
                filters=filters,
                aggregation_method=payload.aggregation_method,
            ),
            domain=payload.domain,
            mode=payload.mode,
            property_id=payload.property_id,
            property_name=payload.property_name,
            metric_name=payload.metric_name,
            dimensions=dimensions,
            series=series,
            target_date=payload.target_date.isoformat() if payload.target_date else series[-1].date,
            metadata={
                "aggregation_method": payload.aggregation_method,
                "corporation": payload.corporation,
                "date_start": date_start,
                "date_end": date_end,
                "filters": filters,
                "target_events": payload.target_events or [],
            },
        )

    @staticmethod
    def to_dataframe(task: AnalysisTask) -> pd.DataFrame:
        df = pd.DataFrame(
            [{"ds": item.date, "y": item.value} for item in task.series]
        )
        df["ds"] = pd.to_datetime(df["ds"])
        return df

    @staticmethod
    def build_analysis_id(
        property_id: str,
        property_name: str,
        corporation: str,
        domain: str,
        mode: str,
        metric_name: str,
        dimensions: Dict[str, Any],
        date_start: str,
        date_end: str,
        filters: Dict[str, Any],
        aggregation_method: str,
    ) -> str:
        signature = {
            "aggregation_method": aggregation_method,
            "corporation": corporation,
            "date_end": date_end,
            "date_start": date_start,
            "dimensions": dimensions,
            "domain": domain,
            "filters": filters,
            "metric_name": metric_name,
            "mode": mode,
            "property_id": property_id,
            "property_name": property_name,
        }
        encoded_signature = json.dumps(signature, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha1(encoded_signature.encode("utf-8")).hexdigest()[:12]
        return f"{property_id}:{domain}:{mode}:{metric_name}:{digest}"
