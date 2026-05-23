"""Simulation API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.models import (
    SimulateRequest,
    SimulateResponse,
    SimulationRecordResponse,
)
from app.services.simulator import (
    get_simulation,
    get_simulations,
    run_simulation,
    save_simulation,
)

router = APIRouter(tags=["Simulation"])


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    status_code=200,
    summary="Run material prep and coating simulation",
    description=(
        "Simulates rocket panel material preparation and protective coating "
        "for a given material, coating type, and panel dimensions. Returns "
        "prep time, coating thickness, process duration, and waste estimates. "
        "The result is persisted to the database."
    ),
)
async def simulate(
    request: SimulateRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulateResponse:
    """Run the RocketPrep simulator and save the result."""
    result = run_simulation(request)
    await save_simulation(db, result)
    return result


@router.get(
    "/simulations",
    response_model=list[SimulationRecordResponse],
    summary="List all simulation runs",
    description="Returns every persisted simulation, ordered by most recent first.",
)
async def list_simulations(
    db: AsyncSession = Depends(get_db),
) -> list[SimulationRecordResponse]:
    """Return all stored simulation records."""
    records = await get_simulations(db)
    return [SimulationRecordResponse.model_validate(r) for r in records]


@router.get(
    "/simulations/{record_id}",
    response_model=SimulationRecordResponse,
    summary="Get a simulation run by id",
    description="Returns a single persisted simulation or 404 if not found.",
)
async def get_simulation_by_id(
    record_id: int,
    db: AsyncSession = Depends(get_db),
) -> SimulationRecordResponse:
    """Return one stored simulation record."""
    record = await get_simulation(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationRecordResponse.model_validate(record)
