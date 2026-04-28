import pandas as pd
import logging
from typing import Dict, Any
from ..domain.schemas import AnomalyRequest, AnalysisResult, ForecastData
from ..ml.base_detector import BaseDetector
from ..infrastructure.json_storage import JSONStorage  # 정확한 구현체 임포트

logger = logging.getLogger(__name__)

class AnomalyService:
    """
    GA4 이상 탐지 비즈니스 로직을 수행합니다. [cite: 2026-02-26]
    의존성 주입(DI)을 통해 모델(Detector)과 저장소(Storage)를 제어합니다.
    """
    def __init__(self, detector: BaseDetector, storage: JSONStorage):
        self.detector = detector
        self.storage = storage

    def run_analysis(self, payload: AnomalyRequest) -> Dict[str, Any]:
        try:
            # 1. 데이터 준비 (Pydantic -> DataFrame)
            df = pd.DataFrame([item.dict() for item in payload.history_data])
            df.rename(columns={'date': 'ds', 'sessions': 'y'}, inplace=True)
            df['ds'] = pd.to_datetime(df['ds'])

            # 2. 모델 실행 (학습 및 예측)
            forecast = self.detector.train_and_predict(df)

            # 3. 이상치 판별 로직
            target_actual = df['y'].iloc[-1]
            target_lower = forecast['yhat_lower'].iloc[-1]
            target_upper = forecast['yhat_upper'].iloc[-1]

            is_anomaly = self.detector.check_anomaly(
                actual=target_actual,
                lower=target_lower,
                upper=target_upper
            )

            # 4. 결과 객체 조립 (Domain Schema 준수)
            result = AnalysisResult(
                property_name=payload.property_name,
                is_anomaly=is_anomaly,
                last_sessions=int(target_actual),
                updated_at=payload.target_date,
                forecast_data=ForecastData(
                    ds=forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
                    y=df['y'].tolist(),
                    yhat=forecast['yhat'].round(2).tolist(),
                    yhat_lower=forecast['yhat_lower'].round(2).tolist(),
                    yhat_upper=forecast['yhat_upper'].round(2).tolist()
                )
            )

            # 5. 저장소 영속화
            self.storage.save(payload.property_id, result.dict())

            return {"status": "success", "is_anomaly": is_anomaly}

        except Exception as e:
            logger.error(f"분석 서비스 실행 중 오류: {str(e)}")
            raise e