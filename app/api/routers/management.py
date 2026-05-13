# app/api/routers/management.py
from fastapi import APIRouter, Depends
from ...infrastructure.json_storage import JSONStorage

router = APIRouter()

@router.post("/reset")
async def reset(storage: JSONStorage = Depends(JSONStorage)):
    cleared_files = storage.clear_all_analysis_files()
    return {"message": "Databases cleared", "cleared_files": cleared_files}

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
