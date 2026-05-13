import hashlib
import json
from typing import Any, Dict, List, Optional

import pandas as pd

from ..domain.generic_schemas import (
    GenericAnalysisRequest,
    UnassignedTrafficDetectionRequest,
    UnassignedTrafficDiagnosisRequest,
)
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
                theme_id=payload.theme_id,
                metric_type=payload.metric_type,
                alert_direction_policy=payload.alert_direction_policy,
            ),
            domain=payload.domain,
            mode=payload.mode,
            property_id=payload.property_id,
            property_name=payload.property_name,
            theme_id=payload.theme_id,
            metric_name=payload.metric_name,
            metric_type=payload.metric_type,
            alert_direction_policy=payload.alert_direction_policy,
            dimensions=dimensions,
            series=series,
            target_date=payload.target_date.isoformat() if payload.target_date else series[-1].date,
            metadata={
                "aggregation_method": payload.aggregation_method,
                "alert_direction_policy": payload.alert_direction_policy,
                "corporation": payload.corporation,
                "date_start": date_start,
                "date_end": date_end,
                "filters": filters,
                "metric_type": payload.metric_type,
                "theme_id": payload.theme_id,
                "target_events": payload.target_events or [],
            },
        )

    @staticmethod
    def from_unassigned_traffic_detection(
        payload: UnassignedTrafficDetectionRequest,
    ) -> AnalysisTask:
        totals: Dict[str, float] = {}
        unassigned: Dict[str, float] = {}

        for row in payload.rows:
            row_date = row.date.isoformat()
            sessions = float(row.sessions)
            totals[row_date] = totals.get(row_date, 0.0) + sessions
            if row.sessionDefaultChannelGroup == "Unassigned":
                unassigned[row_date] = unassigned.get(row_date, 0.0) + sessions

        series = []
        for row_date in sorted(totals):
            total_sessions = totals[row_date]
            unassigned_sessions = unassigned.get(row_date, 0.0)
            value = unassigned_sessions / total_sessions if total_sessions else 0.0
            series.append(TimeSeriesPoint(date=row_date, value=value))

        date_start = payload.date_start.isoformat() if payload.date_start else series[0].date
        date_end = payload.date_end.isoformat() if payload.date_end else series[-1].date
        target_date = payload.target_date.isoformat() if payload.target_date else series[-1].date
        filters = {
            "denominator": "total_sessions",
            "numerator_filter": "sessionDefaultChannelGroup == Unassigned",
            "source_dimension": "sessionDefaultChannelGroup",
            "source_metric": "sessions",
        }

        return AnalysisTask(
            analysis_id=TimeSeriesNormalizer.build_analysis_id(
                property_id=payload.property_id,
                property_name=payload.property_name,
                corporation=payload.corporation,
                domain="traffic_quality",
                mode="detection",
                metric_name="unassigned_session_share",
                dimensions={},
                date_start=date_start,
                date_end=date_end,
                filters=filters,
                aggregation_method="derived_ratio",
                theme_id="unassigned_traffic",
                metric_type="derived_ratio",
                alert_direction_policy="upper_only",
            ),
            domain="traffic_quality",
            mode="detection",
            property_id=payload.property_id,
            property_name=payload.property_name,
            theme_id="unassigned_traffic",
            metric_name="unassigned_session_share",
            metric_type="derived_ratio",
            alert_direction_policy="upper_only",
            dimensions={},
            series=series,
            target_date=target_date,
            metadata={
                "alert_direction_policy": "upper_only",
                "corporation": payload.corporation,
                "date_start": date_start,
                "date_end": date_end,
                "denominator": "total_sessions",
                "filters": filters,
                "metric_type": "derived_ratio",
                "numerator_filter": "sessionDefaultChannelGroup == Unassigned",
                "source_dimension": "sessionDefaultChannelGroup",
                "source_metric": "sessions",
                "theme_id": "unassigned_traffic",
                "total_sessions_by_date": totals,
                "unassigned_sessions_by_date": unassigned,
            },
        )

    @staticmethod
    def from_unassigned_traffic_diagnosis(
        payload: UnassignedTrafficDiagnosisRequest,
    ) -> List[AnalysisTask]:
        dates = sorted({row.date.isoformat() for row in payload.rows})
        target_date = payload.target_date.isoformat() if payload.target_date else dates[-1]
        date_start = payload.date_start.isoformat() if payload.date_start else dates[0]
        date_end = payload.date_end.isoformat() if payload.date_end else dates[-1]

        segment_values: Dict[str, Dict[str, float]] = {}
        raw_values: Dict[str, List[Optional[str]]] = {}
        for row in payload.rows:
            dimension_value = TimeSeriesNormalizer.normalize_unassigned_dimension_value(
                row.sessionSourceMedium
            )
            row_date = row.date.isoformat()
            segment_values.setdefault(dimension_value, {})
            segment_values[dimension_value][row_date] = (
                segment_values[dimension_value].get(row_date, 0.0) + float(row.sessions)
            )
            raw_values.setdefault(dimension_value, [])
            if row.sessionSourceMedium not in raw_values[dimension_value]:
                raw_values[dimension_value].append(row.sessionSourceMedium)

        selected_segments = TimeSeriesNormalizer._select_diagnosis_segments(
            segment_values,
            target_date,
            top_n=payload.top_n,
            min_total_value=payload.min_total_value,
        )
        filters = {
            "diagnosis_dimension": "sessionSourceMedium",
            "filter": "sessionDefaultChannelGroup == Unassigned",
            "source_metric": "sessions",
        }

        tasks = []
        for dimension_value in selected_segments:
            series = [
                TimeSeriesPoint(
                    date=row_date,
                    value=segment_values[dimension_value].get(row_date, 0.0),
                )
                for row_date in dates
            ]
            dimensions = {
                "dimension": "sessionSourceMedium",
                "dimension_value": dimension_value,
            }
            task_filters = {
                **filters,
                "dimension_value": dimension_value,
            }
            tasks.append(
                AnalysisTask(
                    analysis_id=TimeSeriesNormalizer.build_analysis_id(
                        property_id=payload.property_id,
                        property_name=payload.property_name,
                        corporation=payload.corporation,
                        domain="traffic_quality",
                        mode="diagnosis",
                        metric_name="sessions",
                        dimensions=dimensions,
                        date_start=date_start,
                        date_end=date_end,
                        filters=task_filters,
                        aggregation_method="sum",
                        theme_id="unassigned_traffic",
                        metric_type="raw_count",
                        alert_direction_policy="upper_only",
                    ),
                    domain="traffic_quality",
                    mode="diagnosis",
                    property_id=payload.property_id,
                    property_name=payload.property_name,
                    theme_id="unassigned_traffic",
                    metric_name="sessions",
                    metric_type="raw_count",
                    alert_direction_policy="upper_only",
                    dimensions=dimensions,
                    series=series,
                    target_date=target_date,
                    metadata={
                        "alert_direction_policy": "upper_only",
                        "corporation": payload.corporation,
                        "date_start": date_start,
                        "date_end": date_end,
                        "diagnosis_dimension": "sessionSourceMedium",
                        "dimension_value": dimension_value,
                        "filter": "sessionDefaultChannelGroup == Unassigned",
                        "filters": task_filters,
                        "metric_type": "raw_count",
                        "min_total_value": payload.min_total_value,
                        "parent_theme_id": "unassigned_traffic",
                        "raw_dimension_values": raw_values.get(dimension_value, []),
                        "target_date": target_date,
                        "theme_id": "unassigned_traffic",
                        "top_n": payload.top_n,
                    },
                )
            )
        return tasks

    @staticmethod
    def normalize_unassigned_dimension_value(value: Optional[str]) -> str:
        if value is None:
            return "(not set)"
        if value == "":
            return "(empty)"
        return value

    @staticmethod
    def _select_diagnosis_segments(
        segment_values: Dict[str, Dict[str, float]],
        target_date: str,
        top_n: int,
        min_total_value: float,
    ) -> List[str]:
        candidates = []
        for dimension_value, values_by_date in segment_values.items():
            total_value = sum(values_by_date.values())
            target_value = values_by_date.get(target_date, 0.0)
            if total_value >= min_total_value or target_value > 0:
                candidates.append((dimension_value, total_value, target_value))

        candidates.sort(key=lambda item: (not item[2] > 0, -item[1], -item[2], item[0]))
        return [dimension_value for dimension_value, _, _ in candidates[:top_n]]

    @staticmethod
    def build_theme_group_key(
        property_id: Optional[str],
        domain: str,
        theme_id: Optional[str],
        target_date: Optional[str],
    ) -> str:
        return ":".join([property_id or "", domain, theme_id or "", target_date or ""])

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
        theme_id: str = None,
        metric_type: str = None,
        alert_direction_policy: str = "two_sided",
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
        if theme_id:
            signature["theme_id"] = theme_id
        if metric_type:
            signature["metric_type"] = metric_type
        if alert_direction_policy != "two_sided":
            signature["alert_direction_policy"] = alert_direction_policy
        encoded_signature = json.dumps(signature, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha1(encoded_signature.encode("utf-8")).hexdigest()[:12]
        return f"{property_id}:{domain}:{mode}:{metric_name}:{digest}"
