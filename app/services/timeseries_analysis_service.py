from typing import Any, Dict, Optional

from ..domain.generic_schemas import GenericAnalysisRequest, UnassignedTrafficDiagnosisRequest
from ..domain.timeseries import AnalysisResult, AnalysisTask, calculate_point_anomalies
from ..infrastructure.json_storage import JSONStorage
from ..ml.base_detector import BaseDetector
from .alert_policy import summarize_alert_policy
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
        allow_all_zero = self._allows_all_zero_series(task)
        self._validate_input_dataframe(df, allow_all_zero=allow_all_zero)
        if allow_all_zero and (df["y"] == 0).all():
            return self._build_zero_baseline_result(task, df)

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
            theme_id=task.theme_id,
            metric_name=task.metric_name,
            metric_type=task.metric_type,
            alert_direction_policy=task.alert_direction_policy,
            dimensions=task.dimensions,
            metadata=task.metadata,
            is_anomaly=is_anomaly,
            actual_value=actual,
            lower_bound=lower,
            upper_bound=upper,
            target_date=task.target_date or task.series[-1].date,
            forecast_data=forecast_data,
        )

    def analyze(self, task: AnalysisTask) -> AnalysisResult:
        return self.run_single_metric_analysis(task)

    def run_unassigned_traffic_detection(self, payload) -> Dict[str, Any]:
        task = TimeSeriesNormalizer.from_unassigned_traffic_detection(payload)
        result = self.run_single_metric_analysis(task)
        result_dict = result.model_dump(mode="json")
        alert_summary = summarize_alert_policy(
            result.forecast_data,
            result.target_date,
            result.alert_direction_policy,
        )

        if self.storage:
            self.storage.save_generic_analysis(result.analysis_id, result_dict)

        return {
            "status": "success",
            "analysis_id": result.analysis_id,
            "is_anomaly": result.is_anomaly,
            "theme_id": result.theme_id,
            "target_date": alert_summary["target_date"],
            "target_point": alert_summary["target_point"],
            "alert_status": alert_summary["alert_status"],
            "is_current_anomaly": alert_summary["is_current_anomaly"],
            "recent_anomaly_count": alert_summary["recent_anomaly_count"],
            "historical_anomaly_count": alert_summary["historical_anomaly_count"],
            "should_run_diagnosis": alert_summary["alert_status"] == "alert",
            "result": result_dict,
            "next_action": None,
        }

    def run_unassigned_traffic_diagnosis(
        self,
        payload: UnassignedTrafficDiagnosisRequest,
    ) -> Dict[str, Any]:
        tasks = TimeSeriesNormalizer.from_unassigned_traffic_diagnosis(payload)
        items = []
        target_date = payload.target_date.isoformat() if payload.target_date else None

        for task in tasks:
            result = self.run_single_metric_analysis(task)
            result_dict = result.model_dump(mode="json")
            alert_summary = summarize_alert_policy(
                result.forecast_data,
                result.target_date,
                result.alert_direction_policy,
            )
            group_key = TimeSeriesNormalizer.build_theme_group_key(
                result.property_id,
                result.domain,
                result.theme_id,
                alert_summary["target_date"],
            )

            if self.storage:
                self.storage.save_generic_analysis(result.analysis_id, result_dict)

            dimension = result.dimensions.get("dimension")
            dimension_value = result.dimensions.get("dimension_value")
            target_date = alert_summary["target_date"]
            items.append(
                {
                    "analysis_id": result.analysis_id,
                    "theme_id": result.theme_id,
                    "domain": result.domain,
                    "mode": result.mode,
                    "metric_name": result.metric_name,
                    "dimension": dimension,
                    "dimension_value": dimension_value,
                    "target_date": alert_summary["target_date"],
                    "target_point": alert_summary["target_point"],
                    "alert_status": alert_summary["alert_status"],
                    "is_current_anomaly": alert_summary["is_current_anomaly"],
                    "recent_anomaly_count": alert_summary["recent_anomaly_count"],
                    "historical_anomaly_count": alert_summary["historical_anomaly_count"],
                    "forecast_data": result.forecast_data,
                    "group_key": group_key,
                    "result": result_dict,
                }
            )

        return {
            "status": "success",
            "theme_id": "unassigned_traffic",
            "domain": "traffic_quality",
            "mode": "diagnosis",
            "property_id": payload.property_id,
            "property_name": payload.property_name,
            "target_date": target_date,
            "items": items,
        }

    def _validate_input_dataframe(self, df, allow_all_zero: bool = False):
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
        if not allow_all_zero and (numeric_y == 0).all():
            raise ValueError("Time series cannot be all zero")

    def _allows_all_zero_series(self, task: AnalysisTask) -> bool:
        return (
            task.theme_id == "unassigned_traffic"
            and task.metric_type == "derived_ratio"
        )

    def _build_zero_baseline_result(self, task: AnalysisTask, df) -> AnalysisResult:
        forecast_data = {
            "ds": df["ds"].dt.strftime("%Y-%m-%d").tolist(),
            "y": df["y"].tolist(),
            "yhat": [0.0 for _ in range(len(df))],
            "yhat_lower": [0.0 for _ in range(len(df))],
            "yhat_upper": [0.0 for _ in range(len(df))],
            "is_anomaly": [False for _ in range(len(df))],
        }

        return AnalysisResult(
            analysis_id=task.analysis_id,
            domain=task.domain,
            mode=task.mode,
            property_id=task.property_id,
            property_name=task.property_name,
            theme_id=task.theme_id,
            metric_name=task.metric_name,
            metric_type=task.metric_type,
            alert_direction_policy=task.alert_direction_policy,
            dimensions=task.dimensions,
            metadata=task.metadata,
            is_anomaly=False,
            actual_value=0.0,
            lower_bound=0.0,
            upper_bound=0.0,
            target_date=task.target_date or task.series[-1].date,
            forecast_data=forecast_data,
        )

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
