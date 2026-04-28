# app/ml/prophet_detector.py
import pandas as pd  # <--- 이 줄이 누락되어 NameError가 발생했습니다.
from prophet import Prophet
from .base_detector import BaseDetector
from ..core.config import settings

class ProphetDetector(BaseDetector):
    def train_and_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prophet 모델을 사용하여 학습 및 미래 예측 수행"""
        model = Prophet(
            interval_width=settings.PROPHET_INTERVAL_WIDTH,
            yearly_seasonality=False,
            daily_seasonality=False
        )
        # 마지막 타겟 데이터를 제외하고 학습 (Phase 2: 통제)
        model.fit(df.iloc[:-1])

        # 전체 기간에 대한 예측 수행
        return model.predict(df[['ds']])