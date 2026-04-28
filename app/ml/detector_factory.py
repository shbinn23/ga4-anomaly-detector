from .base_detector import BaseDetector
from .prophet_detector import ProphetDetector

class DetectorFactory:
    """분석 모델 생성을 전담하는 팩토리 클래스"""

    @staticmethod
    def get_detector(model_type: str = "prophet") -> BaseDetector:
        """
        요청된 타입에 맞는 탐지기 인스턴스를 반환합니다.
        - 2026년 4월 현재: 'prophet'만 지원
        - 향후 확장: 'timesfm', 'tft' 등 추가 가능
        """
        detectors = {
            "prophet": ProphetDetector,
            # "timesfm": TimesFMDetector, # 향후 확장 포인트
        }

        detector_class = detectors.get(model_type.lower())

        if not detector_class:
            raise ValueError(f"Unsupported model type: {model_type}")

        return detector_class()