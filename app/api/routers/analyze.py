from fastapi import APIRouter, Depends
from ...domain.schemas import AnomalyRequest, BatchAnomalyRequest
from ...services.anomaly_service import AnomalyService
from ...core.dependencies import get_anomaly_service

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

# app/api/routers/analyze.py 수정[cite: 16]

from fastapi import APIRouter, Depends
# ChannelUpdateTask 임포트 추가 필수
from ...domain.schemas import AnomalyRequest, BatchAnomalyRequest, ChannelUpdateTask
from ...services.anomaly_service import AnomalyService
from ...core.dependencies import get_anomaly_service

router = APIRouter()

# ... 기존 analyze, analyze_batch 코드 유지[cite: 16] ...

@router.post("/update-channels")
async def update_channels(
        payload: ChannelUpdateTask,
        service: AnomalyService = Depends(get_anomaly_service)
):
    """
    n8n의 채널 분석 데이터를 수신하는 엔드포인트입니다.[cite: 12, 23]
    """
    return service.run_channel_analysis(payload)