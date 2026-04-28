from abc import ABC, abstractmethod
import pandas as pd

class BaseDetector(ABC):
    @abstractmethod
    def train_and_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """모델을 학습하고 전체 시계열에 대한 예측값을 반환합니다."""
        pass

    def check_anomaly(self, actual: float, lower: float, upper: float) -> bool:
        """이상치 판별 논리 (공통 사용)"""
        return bool(actual < lower or actual > upper)