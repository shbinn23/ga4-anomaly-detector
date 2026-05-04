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
