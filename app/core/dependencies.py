from ..services.anomaly_service import AnomalyService
from ..ml.prophet_detector import ProphetDetector
from ..infrastructure.json_storage import JSONStorage

def get_anomaly_service() -> AnomalyService:
    """FastAPI Depends를 위한 의존성 주입 함수입니다."""
    detector = ProphetDetector()
    storage = JSONStorage()
    return AnomalyService(detector=detector, storage=storage)