from typing import Any, Dict, Optional

from ..domain.generic_schemas import GenericAnalysisRequest
from ..domain.timeseries import AnalysisResult, AnalysisTask, calculate_point_anomalies
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
        result_dict = result.model_dump(mode="json")

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
        self._validate_input_dataframe(df)
        forecast = self.detector.train_and_predict(df)
        self._validate_forecast_dataframe(forecast)

        actual = float(df["y"].iloc[-1])
        lower = float(forecast["yhat_lower"].iloc[-1])
        upper = float(forecast["yhat_upper"].iloc[-1])

        is_anomaly = self.detector.check_anomaly(actual=actual, lower=lower, upper=upper)
        forecast_data = {
            "ds": forecast["ds"].dt.strftime("%Y-%m-%d").tolist(),
            "y": df["y"].tolist(),
            "yhat": forecast["yhat"].round(2).tolist(),
            "yhat_lower": forecast["yhat_lower"].round(2).tolist(),
            "yhat_upper": forecast["yhat_upper"].round(2).tolist(),
        }
        forecast_data["is_anomaly"] = calculate_point_anomalies(forecast_data)

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
            forecast_data=forecast_data,
        )

    def analyze(self, task: AnalysisTask) -> AnalysisResult:
        return self.run_single_metric_analysis(task)

    def _validate_input_dataframe(self, df):
        required_columns = {"ds", "y"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing time series columns: {sorted(missing_columns)}")
        if df["ds"].isna().any():
            raise ValueError("Time series contains missing ds values")
        if df["y"].isna().any():
            raise ValueError("Time series y values must be finite")
        if df["ds"].duplicated().any():
            raise ValueError("Time series contains duplicate ds values")

        numeric_y = df["y"]
        if not numeric_y.map(lambda value: isinstance(value, (int, float))).all():
            raise ValueError("Time series y values must be numeric")
        if not numeric_y.map(lambda value: value == value and value not in (float("inf"), float("-inf"))).all():
            raise ValueError("Time series y values must be finite")
        if df["ds"].nunique() < 2:
            raise ValueError("Time series requires at least two unique ds values")
        if (numeric_y == 0).all():
            raise ValueError("Time series cannot be all zero")

    def _validate_forecast_dataframe(self, forecast):
        required_columns = {"ds", "yhat", "yhat_lower", "yhat_upper"}
        missing_columns = required_columns - set(forecast.columns)
        if missing_columns:
            raise ValueError(f"Missing forecast columns: {sorted(missing_columns)}")
        if forecast[list(required_columns)].isna().any().any():
            raise ValueError("Forecast contains missing values")
        if not (
            (forecast["yhat_lower"] <= forecast["yhat"])
            & (forecast["yhat"] <= forecast["yhat_upper"])
        ).all():
            raise ValueError("Forecast bounds must satisfy yhat_lower <= yhat <= yhat_upper")

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
