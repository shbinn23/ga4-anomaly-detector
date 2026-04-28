# app/api/routers/analyze.py
from fastapi import APIRouter, Depends
from ...domain.schemas import AnomalyRequest
from ...services.anomaly_service import AnomalyService
from ...core.dependencies import get_anomaly_service

# 'app' 대신 'router'를 생성합니다.
router = APIRouter()

# @app.post가 아니라 @router.post를 사용해야 합니다.
@router.post("/analyze")
async def analyze(
        payload: AnomalyRequest,
        service: AnomalyService = Depends(get_anomaly_service)
):
    return service.run_analysis(payload)