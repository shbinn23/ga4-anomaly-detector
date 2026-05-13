from typing import Any, Dict, Optional

from ..domain.generic_schemas import GenericAnalysisRequest
from ..domain.timeseries import AnalysisResult, AnalysisTask
from ..infrastructure.json_storage import JSONStorage
from ..ml.base_detector import BaseDetector
from .timeseries_normalizer import TimeSeriesNormalizer


class TimeSeriesAnalysisService:
    """Runs anomaly detection for canonical single-metric time series tasks."""

    def __init__(self, detector: BaseDetector, storage: Optional[JSONStorage] = None):
        self.detector = detector
        self.storage = storage

    def run_generic_analysis(self, payload: GenericAnalysisRequest) -> Dict[str, Any]:
        task = TimeSeriesNormalizer.from_generic_request(payload)
        result = self.run_single_metric_analysis(task)
        result_dict = result.model_dump()

        if self.storage:
            self.storage.save_generic_analysis(result.analysis_id, result_dict)

        return {
            "status": "success",
            "analysis_id": result.analysis_id,
            "is_anomaly": result.is_anomaly,
            "result": result_dict,
            "next_action": self._build_next_action(payload, result),
        }

    def run_single_metric_analysis(self, task: AnalysisTask) -> AnalysisResult:
        df = TimeSeriesNormalizer.to_dataframe(task)
        forecast = self.detector.train_and_predict(df)

        actual = float(df["y"].iloc[-1])
        lower = float(forecast["yhat_lower"].iloc[-1])
        upper = float(forecast["yhat_upper"].iloc[-1])

        is_anomaly = self.detector.check_anomaly(actual=actual, lower=lower, upper=upper)
        point_anomalies = [False] * (len(df) - 1) + [is_anomaly]

        return AnalysisResult(
            analysis_id=task.analysis_id,
            domain=task.domain,
            mode=task.mode,
            property_id=task.property_id,
            property_name=task.property_name,
            metric_name=task.metric_name,
            dimensions=task.dimensions,
            is_anomaly=is_anomaly,
            actual_value=actual,
            lower_bound=lower,
            upper_bound=upper,
            target_date=task.target_date or task.series[-1].date,
            forecast_data={
                "ds": forecast["ds"].dt.strftime("%Y-%m-%d").tolist(),
                "y": df["y"].tolist(),
                "yhat": forecast["yhat"].round(2).tolist(),
                "yhat_lower": forecast["yhat_lower"].round(2).tolist(),
                "yhat_upper": forecast["yhat_upper"].round(2).tolist(),
                "is_anomaly": point_anomalies,
            },
        )

    def analyze(self, task: AnalysisTask) -> AnalysisResult:
        return self.run_single_metric_analysis(task)

    def _build_next_action(
        self,
        payload: GenericAnalysisRequest,
        result: AnalysisResult,
    ) -> Optional[Dict[str, Any]]:
        if payload.mode != "detection" or not result.is_anomaly or not payload.target_events:
            return None

        return {
            "type": "request_diagnosis",
            "domain": payload.domain,
            "property_id": payload.property_id,
            "metric_name": payload.metric_name,
            "dimensions": ["eventName"],
            "target_events": payload.target_events,
        }
