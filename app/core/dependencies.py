from ..services.anomaly_service import AnomalyService
from ..services.timeseries_analysis_service import TimeSeriesAnalysisService
from ..ml.prophet_detector import ProphetDetector
from ..infrastructure.json_storage import JSONStorage

def get_anomaly_service() -> AnomalyService:
    """FastAPI Depends를 위한 의존성 주입 함수입니다."""
    detector = ProphetDetector()
    storage = JSONStorage()
    return AnomalyService(detector=detector, storage=storage)

def get_timeseries_analysis_service() -> TimeSeriesAnalysisService:
    """Generic single-metric analysis service for n8n-driven payloads."""
    detector = ProphetDetector()
    storage = JSONStorage()
    return TimeSeriesAnalysisService(detector=detector, storage=storage)
