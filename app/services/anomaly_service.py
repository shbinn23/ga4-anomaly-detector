import gc
import pandas as pd
import logging
from typing import Dict, Any
from ..domain.schemas import AnomalyRequest, BatchAnomalyRequest, AnalysisResult, ForecastData, ChannelUpdateTask
from ..ml.base_detector import BaseDetector
from ..infrastructure.json_storage import JSONStorage

logger = logging.getLogger(__name__)

class AnomalyService:
    def __init__(self, detector: BaseDetector, storage: JSONStorage):
        self.detector = detector
        self.storage = storage

    def _analyze_single(self, payload: AnomalyRequest) -> AnalysisResult:
        """단일 Property에 대한 Prophet 분석을 수행하고 결과를 반환합니다. 저장은 호출자가 담당합니다."""
        df = pd.DataFrame([item.dict() for item in payload.history_data])
        df.rename(columns={'date': 'ds', 'sessions': 'y'}, inplace=True)
        df['ds'] = pd.to_datetime(df['ds'])

        forecast = self.detector.train_and_predict(df)

        target_actual = df['y'].iloc[-1]
        target_lower = forecast['yhat_lower'].iloc[-1]
        target_upper = forecast['yhat_upper'].iloc[-1]

        is_anomaly = self.detector.check_anomaly(
            actual=target_actual,
            lower=target_lower,
            upper=target_upper
        )

        return AnalysisResult(
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

    def run_analysis(self, payload: AnomalyRequest) -> Dict[str, Any]:
        try:
            result = self._analyze_single(payload)
            self.storage.save(payload.property_id, result.dict())
            return {"status": "success", "is_anomaly": result.is_anomaly}
        except Exception as e:
            logger.error(f"단일 분석 중 오류: {str(e)}")
            raise

    def run_batch_analysis(self, payload: BatchAnomalyRequest) -> Dict[str, Any]:
        try:
            data_map = {}
            results = []
            for item in payload.properties:
                result = self._analyze_single(item)
                data_map[item.property_id] = result.dict()
                results.append({
                    "property_id": item.property_id,
                    "property_name": item.property_name,
                    "is_anomaly": result.is_anomaly,
                })

            self.storage.save_batch(data_map)
            return {
                "status": "success",
                "processed": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"배치 분석 중 오류: {str(e)}")
            raise

    def run_channel_analysis(self, payload: ChannelUpdateTask) -> Dict[str, Any]:
        analysis_results = {}
        processed_count = 0

        for prop in payload.data:
            prop_id = prop.property_id
            prop_channels = {}

            logger.info(f"Processing Property: {prop_id} ({prop.property_name})")

            for channel_name, history in prop.grouped_channels.items():
                try:
                    # 1. 데이터 검증: 최소 데이터 포인트 확인 (Prophet은 최소 2개 필요)[cite: 7, 9]
                    if len(history) < 2:
                        logger.warning(f"Skipping {channel_name}: Not enough data points.")
                        continue

                    df = pd.DataFrame([h.dict() for h in history])
                    df.rename(columns={'date': 'ds', 'sessions': 'y'}, inplace=True)
                    df['ds'] = pd.to_datetime(df['ds'])

                    # 2. 분석 실행[cite: 7, 21]
                    forecast = self.detector.train_and_predict(df)

                    is_anomaly = self.detector.check_anomaly(
                        actual=df['y'].iloc[-1],
                        lower=forecast['yhat_lower'].iloc[-1],
                        upper=forecast['yhat_upper'].iloc[-1]
                    )

                    prop_channels[channel_name] = {
                        "is_anomaly": is_anomaly,
                        "last_sessions": int(df['y'].iloc[-1]),
                        "forecast_data": {
                            "ds": forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
                            "y": df['y'].tolist(),
                            "yhat": forecast['yhat'].round(2).tolist(),
                            "yhat_lower": forecast['yhat_lower'].round(2).tolist(),
                            "yhat_upper": forecast['yhat_upper'].round(2).tolist()
                        }
                    }

                    # 3. 메모리 강제 해제 (핵심)
                    del df
                    del forecast
                    gc.collect()

                except Exception as e:
                    logger.error(f"Error in channel {channel_name}: {str(e)}")
                    continue # 한 채널이 터져도 다음 채널 진행

            analysis_results[prop_id] = prop_channels
            processed_count += 1

            # 프로퍼티 단위로도 메모리 정리
            gc.collect()

        # 4. 결과 영속화
        if analysis_results:
            self.storage.save_all_channel_analysis(analysis_results)

        return {"status": "success", "processed_properties": processed_count}