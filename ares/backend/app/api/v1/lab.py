"""Laboratory and Synthetic Demonstration Endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.deps import require_permission
from app.lab.simulator import LabSimulator

router = APIRouter(prefix="/lab", tags=["Lab Mode"])


@router.get("/scenarios", response_model=List[Dict[str, Any]], dependencies=[Depends(require_permission("lab.execute"))])
def get_lab_scenarios():
    return LabSimulator.get_available_scenarios()


@router.get("/scenarios/{scenario_id}/dataset", response_model=Dict[str, Any], dependencies=[Depends(require_permission("lab.execute"))])
def get_scenario_dataset(scenario_id: str):
    return LabSimulator.get_synthetic_dataset(scenario_id)
