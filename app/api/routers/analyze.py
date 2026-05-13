from fastapi import APIRouter, Depends
from ...domain.generic_schemas import GenericAnalysisRequest, GenericAnalysisResponse
from ...domain.schemas import AnomalyRequest, BatchAnomalyRequest, ChannelUpdateTask
from ...services.anomaly_service import AnomalyService
from ...services.timeseries_analysis_service import TimeSeriesAnalysisService
from ...core.dependencies import get_anomaly_service, get_timeseries_analysis_service

# 라우터 인스턴스는 파일 내에서 단 한 번만 생성합니다.
router = APIRouter()

@router.post("/analyze")
async def analyze(
        payload: AnomalyRequest,
        service: AnomalyService = Depends(get_anomaly_service)
):
    return service.run_analysis(payload)

@router.post("/analyze/batch")
async def analyze_batch(
        payload: BatchAnomalyRequest,
        service: AnomalyService = Depends(get_anomaly_service)
):
    return service.run_batch_analysis(payload)

@router.post("/analyze/generic", response_model=GenericAnalysisResponse)
async def analyze_generic(
        payload: GenericAnalysisRequest,
        service: TimeSeriesAnalysisService = Depends(get_timeseries_analysis_service)
):
    return service.run_generic_analysis(payload)

@router.post("/update-channels")
async def update_channels(
        payload: ChannelUpdateTask,
        service: AnomalyService = Depends(get_anomaly_service)
):
    """n8n 하단 브랜치로부터 채널별 데이터를 수신하여 AI 분석을 수행합니다."""
    return service.run_channel_analysis(payload)
