"""Unit and integration tests for the RocketPrep simulator."""

import itertools

from httpx import ASGITransport, AsyncClient
import pytest

from app.core.models import CoatingType, MaterialType, SimulateRequest
from app.main import app
from app.services.simulator import (
    COATING_PROFILES,
    MATERIAL_PROFILES,
    WASTE_PERCENTAGE,
    calculate_coating_cure_time,
    calculate_material_mass,
    calculate_panel_area,
    calculate_prep_time,
    calculate_waste_mass,
    run_simulation,
)

MATERIALS: tuple[MaterialType, ...] = (
    "aluminium_alloy",
    "stainless_steel",
    "carbon_composite",
)
COATINGS: tuple[CoatingType, ...] = (
    "anti_corrosion",
    "thermal_protection",
    "nano_ceramic",
)
MATERIAL_COATING_COMBOS = list(itertools.product(MATERIALS, COATINGS))

PANEL_WIDTH_M = 2.0
PANEL_HEIGHT_M = 2.0
PANEL_AREA_SQM = 4.0

SIMULATE_PAYLOAD = {
    "material": "aluminium_alloy",
    "coating": "anti_corrosion",
    "panel_width_m": PANEL_WIDTH_M,
    "panel_height_m": PANEL_HEIGHT_M,
}


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client wired to the FastAPI app via ASGI transport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _build_request(material: MaterialType, coating: CoatingType) -> SimulateRequest:
    """Create a SimulateRequest for the standard test panel size."""
    return SimulateRequest(
        material=material,
        coating=coating,
        panel_width_m=PANEL_WIDTH_M,
        panel_height_m=PANEL_HEIGHT_M,
    )


# ── Unit tests ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.parametrize(("material", "coating"), MATERIAL_COATING_COMBOS)
def test_run_simulation_all_material_coating_combos(
    material: MaterialType,
    coating: CoatingType,
) -> None:
    """Every material x coating combo produces consistent simulation output."""
    request = _build_request(material, coating)
    result = run_simulation(request)

    material_profile = MATERIAL_PROFILES[material]
    coating_profile = COATING_PROFILES[coating]

    assert result.material == material
    assert result.coating == coating
    assert result.material_display_name == material_profile.display_name
    assert result.coating_display_name == coating_profile.display_name
    assert result.panel_width_m == PANEL_WIDTH_M
    assert result.panel_height_m == PANEL_HEIGHT_M
    assert result.panel_area_sqm == calculate_panel_area(PANEL_WIDTH_M, PANEL_HEIGHT_M)
    assert result.prep_time_minutes == calculate_prep_time(material, PANEL_AREA_SQM)
    assert result.coating_thickness_microns == coating_profile.thickness_microns
    assert result.coating_cure_minutes == calculate_coating_cure_time(
        coating, PANEL_AREA_SQM
    )
    assert result.total_process_time_minutes == (
        result.prep_time_minutes + result.coating_cure_minutes
    )
    assert result.estimated_material_mass_kg == calculate_material_mass(
        material, PANEL_AREA_SQM
    )
    assert result.waste_percentage == WASTE_PERCENTAGE
    assert result.waste_mass_kg == calculate_waste_mass(
        result.estimated_material_mass_kg
    )
    assert material_profile.display_name in result.summary
    assert coating_profile.display_name in result.summary


@pytest.mark.unit
def test_calculate_panel_area() -> None:
    """Panel area is width multiplied by height, rounded to four decimals."""
    assert calculate_panel_area(2.5, 1.8) == 4.5


@pytest.mark.unit
def test_waste_mass_is_eight_percent_of_material_mass() -> None:
    """Waste mass reflects the fixed 8% waste fraction."""
    material_mass = 100.0
    assert calculate_waste_mass(material_mass) == 8.0


# ── Integration tests ─────────────────────────────────────────────────────────────


@pytest.mark.integration
async def test_health_endpoint(client: AsyncClient) -> None:
    """GET /health returns service status."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "rocketprep"}


@pytest.mark.integration
@pytest.mark.parametrize(("material", "coating"), MATERIAL_COATING_COMBOS)
async def test_simulate_endpoint_all_combos(
    client: AsyncClient,
    material: MaterialType,
    coating: CoatingType,
) -> None:
    """POST /api/v1/simulate succeeds for all material x coating combinations."""
    payload = {
        "material": material,
        "coating": coating,
        "panel_width_m": PANEL_WIDTH_M,
        "panel_height_m": PANEL_HEIGHT_M,
    }
    response = await client.post("/api/v1/simulate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["material"] == material
    assert data["coating"] == coating
    assert data["panel_area_sqm"] == PANEL_AREA_SQM
    assert data["waste_percentage"] == WASTE_PERCENTAGE
    assert data["total_process_time_minutes"] == (
        data["prep_time_minutes"] + data["coating_cure_minutes"]
    )

    expected = run_simulation(_build_request(material, coating))
    assert data["prep_time_minutes"] == expected.prep_time_minutes
    assert data["coating_thickness_microns"] == expected.coating_thickness_microns
    assert data["estimated_material_mass_kg"] == expected.estimated_material_mass_kg


@pytest.mark.integration
async def test_simulate_endpoint_matches_service(client: AsyncClient) -> None:
    """POST /api/v1/simulate returns the same result as the service layer."""
    response = await client.post("/api/v1/simulate", json=SIMULATE_PAYLOAD)

    assert response.status_code == 200
    expected = run_simulation(SimulateRequest(**SIMULATE_PAYLOAD))
    assert response.json() == expected.model_dump()


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload",
    [
        {
            "material": "titanium",
            "coating": "anti_corrosion",
            "panel_width_m": 2.0,
            "panel_height_m": 2.0,
        },
        {
            "material": "aluminium_alloy",
            "coating": "epoxy_paint",
            "panel_width_m": 2.0,
            "panel_height_m": 2.0,
        },
        {
            "material": "invalid",
            "coating": "invalid",
            "panel_width_m": 2.0,
            "panel_height_m": 2.0,
        },
    ],
    ids=["invalid_material", "invalid_coating", "invalid_both"],
)
async def test_simulate_rejects_invalid_material_or_coating(
    client: AsyncClient,
    payload: dict[str, object],
) -> None:
    """Invalid material or coating values return HTTP 422."""
    response = await client.post("/api/v1/simulate", json=payload)

    assert response.status_code == 422
