from pathlib import Path
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from ..domain.dashboard_schemas import (
    DashboardForecastData,
    DashboardForecastPoint,
    DashboardResultItem,
)
from ..domain.exceptions import InfrastructureError
from ..domain.timeseries import AnalysisResult
from ..infrastructure.json_storage import JSONStorage


class DashboardResultsService:
    """Read-only adapter from persisted analysis stores to dashboard results."""

    def __init__(self, storage: JSONStorage):
        self.storage = storage

    def list_results(self) -> List[DashboardResultItem]:
        items: List[DashboardResultItem] = []
        items.extend(self._from_session_results(self._read_store(self.storage.path)))
        items.extend(self._from_channel_results(self._read_store(self._store_path("channel_anomaly_db.json"))))
        items.extend(self._from_generic_results(self._read_store(self._store_path("generic_analysis_db.json"))))
        return items

    def _store_path(self, filename: str) -> Path:
        return self.storage.path.parent / filename

    def _read_store(self, path: Path) -> Dict[str, Any]:
        try:
            return self.storage._load_from_path(path)
        except Exception as exc:
            raise InfrastructureError(f"Failed to read dashboard store {path.name}: {exc}") from exc

    def _from_session_results(self, data: Dict[str, Any]) -> List[DashboardResultItem]:
        items: List[DashboardResultItem] = []
        for property_id, result in data.items():
            if not isinstance(result, dict):
                raise InfrastructureError(f"Invalid session result for {property_id}")

            forecast_data = self._forecast_data(result, f"sessions:{property_id}")
            item_id = f"sessions:detection:{property_id}"
            has_anomaly = any(forecast_data.is_anomaly)
            target_point = self._target_point(forecast_data, result.get("updated_at"))
            alert_status = self._alert_status(forecast_data, target_point)
            group_key = self._group_key(str(property_id), "sessions", "sessions", target_point)
            items.append(
                self._item(
                    {
                        "id": item_id,
                        "source": "results_db",
                        "group_key": group_key,
                        "analysis_id": item_id,
                        "domain": "sessions",
                        "mode": "detection",
                        "property_id": str(property_id),
                        "property_name": result.get("property_name"),
                        "metric_name": "sessions",
                        "dimension": None,
                        "dimension_value": None,
                        "dimensions": {},
                        "has_anomaly": has_anomaly,
                        "is_anomaly": bool(result.get("is_anomaly", has_anomaly)),
                        "actual_value": result.get("last_sessions"),
                        "target_date": target_point.ds if target_point else result.get("updated_at"),
                        "target_point": target_point,
                        "is_current_anomaly": bool(target_point.is_anomaly) if target_point else False,
                        "alert_status": alert_status,
                        "historical_anomaly_count": sum(1 for value in forecast_data.is_anomaly if value),
                        "recent_anomaly_count": self._recent_anomaly_count(forecast_data, target_point),
                        "latest_point": target_point,
                        "forecast_data": forecast_data,
                    },
                    f"sessions:{property_id}",
                )
            )
        return items

    def _from_channel_results(self, data: Dict[str, Any]) -> List[DashboardResultItem]:
        items: List[DashboardResultItem] = []
        for property_id, channels in data.items():
            if not isinstance(channels, dict):
                raise InfrastructureError(f"Invalid channel result for {property_id}")
            for dimension_value, result in channels.items():
                if not isinstance(result, dict):
                    raise InfrastructureError(f"Invalid channel result for {property_id}:{dimension_value}")

                forecast_data = self._forecast_data(result, f"channel:{property_id}:{dimension_value}")
                item_id = f"sessions:diagnosis:{property_id}:{dimension_value}"
                has_anomaly = any(forecast_data.is_anomaly)
                target_point = self._target_point(forecast_data, result.get("updated_at"))
                alert_status = self._alert_status(forecast_data, target_point)
                group_key = self._group_key(str(property_id), "sessions", "sessions", target_point)
                items.append(
                    self._item(
                        {
                            "id": item_id,
                            "source": "channel_anomaly_db",
                            "group_key": group_key,
                            "analysis_id": item_id,
                            "domain": "sessions",
                            "mode": "diagnosis",
                            "property_id": str(property_id),
                            "property_name": result.get("property_name"),
                            "metric_name": "sessions",
                            "dimension": "channel",
                            "dimension_value": str(dimension_value),
                            "dimensions": {"dimension": "channel", "dimension_value": str(dimension_value)},
                            "has_anomaly": has_anomaly,
                            "is_anomaly": bool(result.get("is_anomaly", has_anomaly)),
                            "actual_value": result.get("last_sessions"),
                            "target_date": target_point.ds if target_point else result.get("updated_at"),
                            "target_point": target_point,
                            "is_current_anomaly": bool(target_point.is_anomaly) if target_point else False,
                            "alert_status": alert_status,
                            "historical_anomaly_count": sum(1 for value in forecast_data.is_anomaly if value),
                            "recent_anomaly_count": self._recent_anomaly_count(forecast_data, target_point),
                            "latest_point": target_point,
                            "forecast_data": forecast_data,
                        },
                        f"channel:{property_id}:{dimension_value}",
                    )
                )
        return items

    def _from_generic_results(self, data: Dict[str, Any]) -> List[DashboardResultItem]:
        items: List[DashboardResultItem] = []
        for key, raw_result in data.items():
            if not isinstance(raw_result, dict):
                raise InfrastructureError(f"Invalid generic result for {key}")

            try:
                result = AnalysisResult(**raw_result)
            except ValidationError as exc:
                raise InfrastructureError(f"Invalid generic analysis result for {key}: {exc}") from exc

            forecast_data = self._forecast_data(
                result.model_dump(mode="json"),
                f"generic:{key}",
            )
            dimension, dimension_value = self._representative_dimension(result.mode, result.dimensions)
            has_anomaly = any(forecast_data.is_anomaly)
            target_point = self._target_point(forecast_data, result.target_date)
            alert_status = self._alert_status(forecast_data, target_point)
            group_key = self._group_key(result.property_id, result.domain, result.metric_name, target_point)
            item = self._item(
                {
                    "id": str(key),
                    "source": "generic_analysis_db",
                    "group_key": group_key,
                    "analysis_id": result.analysis_id,
                    "domain": result.domain,
                    "mode": result.mode,
                    "property_id": result.property_id,
                    "property_name": result.property_name,
                    "metric_name": result.metric_name,
                    "dimension": dimension,
                    "dimension_value": dimension_value,
                    "dimensions": result.dimensions,
                    "has_anomaly": has_anomaly,
                    "is_anomaly": result.is_anomaly,
                    "actual_value": result.actual_value,
                    "lower_bound": result.lower_bound,
                    "upper_bound": result.upper_bound,
                    "target_date": target_point.ds if target_point else result.target_date,
                    "target_point": target_point,
                    "is_current_anomaly": bool(target_point.is_anomaly) if target_point else False,
                    "alert_status": alert_status,
                    "historical_anomaly_count": sum(1 for value in forecast_data.is_anomaly if value),
                    "recent_anomaly_count": self._recent_anomaly_count(forecast_data, target_point),
                    "latest_point": target_point,
                    "forecast_data": forecast_data,
                },
                f"generic:{key}",
            )
            items.append(item)
        return items

    def _forecast_data(self, result: Dict[str, Any], context: str) -> DashboardForecastData:
        forecast_data = result.get("forecast_data")
        if not isinstance(forecast_data, dict):
            raise InfrastructureError(f"Missing forecast_data for {context}")
        try:
            return DashboardForecastData(**forecast_data)
        except ValidationError as exc:
            raise InfrastructureError(f"Invalid forecast_data for {context}: {exc}") from exc

    def _target_point(
        self,
        forecast_data: DashboardForecastData,
        target_date: Optional[str],
    ) -> Optional[DashboardForecastPoint]:
        if not forecast_data.ds:
            return None
        index = len(forecast_data.ds) - 1
        if target_date in forecast_data.ds:
            index = forecast_data.ds.index(target_date)
        return DashboardForecastPoint(
            ds=forecast_data.ds[index],
            y=forecast_data.y[index],
            yhat=forecast_data.yhat[index],
            yhat_lower=forecast_data.yhat_lower[index],
            yhat_upper=forecast_data.yhat_upper[index],
            is_anomaly=forecast_data.is_anomaly[index],
        )

    def _recent_anomaly_count(
        self,
        forecast_data: DashboardForecastData,
        target_point: Optional[DashboardForecastPoint],
    ) -> int:
        if not target_point or target_point.ds not in forecast_data.ds:
            return 0
        try:
            target_day = date.fromisoformat(target_point.ds)
        except ValueError:
            index = forecast_data.ds.index(target_point.ds)
            start = max(0, index - 6)
            return sum(1 for value in forecast_data.is_anomaly[start : index + 1] if value)

        start_day = target_day - timedelta(days=6)
        count = 0
        for point_date, is_anomaly in zip(forecast_data.ds, forecast_data.is_anomaly):
            try:
                current_day = date.fromisoformat(point_date)
            except ValueError:
                continue
            if start_day <= current_day <= target_day and is_anomaly:
                count += 1
        return count

    def _alert_status(
        self,
        forecast_data: DashboardForecastData,
        target_point: Optional[DashboardForecastPoint],
    ) -> str:
        if not target_point:
            return "normal"
        if target_point.is_anomaly:
            return "alert"
        if self._recent_anomaly_count(forecast_data, target_point) >= 2:
            return "watch"
        return "normal"

    def _group_key(
        self,
        property_id: Optional[str],
        domain: str,
        metric_name: str,
        target_point: Optional[DashboardForecastPoint],
    ) -> str:
        target_date = target_point.ds if target_point else ""
        return ":".join([property_id or "", domain, metric_name, target_date])

    def _representative_dimension(
        self,
        mode: str,
        dimensions: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str]]:
        if mode != "diagnosis" or not dimensions:
            return None, None
        if "dimension" in dimensions and "dimension_value" in dimensions:
            return str(dimensions["dimension"]), str(dimensions["dimension_value"])
        if len(dimensions) == 1:
            dimension, value = next(iter(dimensions.items()))
            return str(dimension), str(value)
        return None, None

    def _item(self, data: Dict[str, Any], context: str) -> DashboardResultItem:
        data["actual_value"] = self._optional_float(data.get("actual_value"))
        data["lower_bound"] = self._optional_float(data.get("lower_bound"))
        data["upper_bound"] = self._optional_float(data.get("upper_bound"))
        try:
            return DashboardResultItem(**data)
        except ValidationError as exc:
            raise InfrastructureError(f"Invalid dashboard result for {context}: {exc}") from exc

    def _optional_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        return float(value)
