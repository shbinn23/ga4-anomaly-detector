# app/api/routers/management.py
from fastapi import APIRouter, Depends
from ...infrastructure.json_storage import JSONStorage

router = APIRouter()

@router.post("/reset")
async def reset(storage: JSONStorage = Depends(JSONStorage)):
    storage.clear()
    return {"message": "Database cleared"}

@router.get("/health")
async def health_check():
    return {"status": "healthy"}