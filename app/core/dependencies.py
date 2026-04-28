from ..services.anomaly_service import AnomalyService
from ..ml.prophet_detector import ProphetDetector
from ..infrastructure.json_storage import JSONStorage

def get_anomaly_service() -> AnomalyService:
    """
    FastAPI Depends를 위한 의존성 주입 함수입니다.
    실제 분석 모델(Prophet)과 저장소(JSON) 인스턴스를 생성하여 서비스에 전달합니다. [cite: 2026-02-26]
    """
    detector = ProphetDetector()
    storage = JSONStorage()
    return AnomalyService(detector=detector, storage=storage)