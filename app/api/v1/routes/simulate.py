"""Simulation API routes."""

from fastapi import APIRouter

from app.core.models import SimulateRequest, SimulateResponse
from app.services.simulator import run_simulation

router = APIRouter(prefix="/simulate", tags=["Simulation"])


@router.post(
    "",
    response_model=SimulateResponse,
    status_code=200,
    summary="Run material prep and coating simulation",
    description=(
        "Simulates rocket panel material preparation and protective coating "
        "for a given material, coating type, and panel dimensions. Returns "
        "prep time, coating thickness, process duration, and waste estimates."
    ),
)
async def simulate(request: SimulateRequest) -> SimulateResponse:
    """Run the RocketPrep simulator for the submitted panel configuration."""
    return run_simulation(request)
