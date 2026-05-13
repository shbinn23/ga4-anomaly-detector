import gc
import logging
from typing import Dict, Any
from ..domain.schemas import AnomalyRequest, BatchAnomalyRequest, AnalysisResult as SessionAnalysisResult, ForecastData, ChannelUpdateTask
from ..domain.timeseries import AnalysisResult, AnalysisTask, TimeSeriesPoint
from ..ml.base_detector import BaseDetector
from ..infrastructure.json_storage import JSONStorage
from .timeseries_analysis_service import TimeSeriesAnalysisService

logger = logging.getLogger(__name__)

class AnomalyService:
    def __init__(self, detector: BaseDetector, storage: JSONStorage):
        self.detector = detector
        self.storage = storage
        self.timeseries_service = TimeSeriesAnalysisService(detector=detector)

    def _analyze_single(self, payload: AnomalyRequest) -> SessionAnalysisResult:
        """단일 Property에 대한 Prophet 분석을 수행하고 결과를 반환합니다. 저장은 호출자가 담당합니다."""
        task = AnalysisTask(
            analysis_id=payload.property_id,
            domain="sessions",
            mode="detection",
            property_id=payload.property_id,
            property_name=payload.property_name,
            metric_name="sessions",
            dimensions={},
            series=[
                TimeSeriesPoint(date=item.date, value=item.sessions)
                for item in payload.history_data
            ],
            target_date=payload.target_date,
        )
        result = self.timeseries_service.run_single_metric_analysis(task)
        return self._to_session_result(result)

    def _to_session_result(self, result: AnalysisResult) -> SessionAnalysisResult:
        return SessionAnalysisResult(
            property_name=result.property_name or "",
            is_anomaly=result.is_anomaly,
            last_sessions=int(result.actual_value),
            updated_at=result.target_date,
            forecast_data=ForecastData(
                ds=result.forecast_data["ds"],
                y=result.forecast_data["y"],
                yhat=result.forecast_data["yhat"],
                yhat_lower=result.forecast_data["yhat_lower"],
                yhat_upper=result.forecast_data["yhat_upper"],
                is_anomaly=result.forecast_data["is_anomaly"],
            )
        )

    def _to_channel_result(self, result: AnalysisResult) -> Dict[str, Any]:
        return {
            "is_anomaly": result.is_anomaly,
            "last_sessions": int(result.actual_value),
            "forecast_data": result.forecast_data,
        }

    def run_analysis(self, payload: AnomalyRequest) -> Dict[str, Any]:
        try:
            result = self._analyze_single(payload)
            result_dict = result.model_dump(mode="json")
            self.storage.save(payload.property_id, result_dict)

            # 🔥 [수정] 껍데기만 보내던 것을 전체 분석 결과 반환으로 변경
            return {
                "status": "success",
                "result": result_dict
            }
        except Exception as e:
            logger.error(f"단일 분석 중 오류: {str(e)}")
            raise

    def run_batch_analysis(self, payload: BatchAnomalyRequest) -> Dict[str, Any]:
        try:
            data_map = {}
            results = []
            for item in payload.properties:
                result = self._analyze_single(item)
                data_map[item.property_id] = result.model_dump(mode="json")
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

                    task = AnalysisTask(
                        analysis_id=f"{prop_id}:sessions:sessions:{channel_name}",
                        domain="sessions",
                        mode="diagnosis",
                        property_id=prop_id,
                        property_name=prop.property_name,
                        metric_name="sessions",
                        dimensions={"channel": channel_name},
                        series=[
                            TimeSeriesPoint(date=item.date, value=item.sessions)
                            for item in history
                        ],
                        target_date=history[-1].date,
                    )
                    result = self.timeseries_service.run_single_metric_analysis(task)
                    prop_channels[channel_name] = self._to_channel_result(result)

                    # 3. 메모리 강제 해제 (핵심)
                    del task
                    del result
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

        # 🔥 [수정] 결과를 반환값에 포함시켰습니다.
        return {
            "status": "success",
            "processed_properties": processed_count,
            "results": analysis_results
        }
