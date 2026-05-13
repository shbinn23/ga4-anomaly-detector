from fastapi import APIRouter, Depends, HTTPException

from ...domain.dashboard_schemas import DashboardResultsResponse
from ...domain.exceptions import InfrastructureError
from ...infrastructure.json_storage import JSONStorage
from ...services.dashboard_results_service import DashboardResultsService

router = APIRouter()


@router.get("/dashboard/results", response_model=DashboardResultsResponse)
async def dashboard_results(storage: JSONStorage = Depends(JSONStorage)):
    try:
        items = DashboardResultsService(storage).list_results()
        return DashboardResultsResponse(items=items)
    except InfrastructureError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
