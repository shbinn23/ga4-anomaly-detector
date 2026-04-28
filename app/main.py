from fastapi import FastAPI
from .api.routers import analyze, management
from .core.config import settings
from .core.logging import setup_logging

# 로깅 설정 초기화
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0"
)

# [핵심 수정] 모든 라우터를 /api/v1 그룹으로 묶어 등록합니다.
app.include_router(analyze.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(management.router, prefix="/api/v1", tags=["Management"])

@app.get("/")
async def root():
    return {"status": "running", "project": settings.PROJECT_NAME}