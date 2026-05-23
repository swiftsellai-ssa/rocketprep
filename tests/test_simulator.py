"""Unit and integration tests for the RocketPrep simulator."""

import itertools

from httpx import AsyncClient
import pytest

from app.core.models import CoatingType, MaterialType, SimulateRequest
from app.services.simulator import (
    COATING_PROFILES,
    MATERIAL_PROFILES,
    calculate_coating_cure_time,
    calculate_material_mass,
    calculate_panel_area,
    calculate_prep_time,
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
    assert result.total_process_time_minutes == sum(
        p.duration_minutes for p in result.prep_phases
    )
    assert result.estimated_material_mass_kg == calculate_material_mass(
        material, PANEL_AREA_SQM
    )
    assert result.waste_percentage == 100 - coating_profile.transfer_efficiency_pct
    assert result.transfer_efficiency_pct == coating_profile.transfer_efficiency_pct
    assert len(result.prep_phases) == 5
    assert material_profile.display_name in result.summary
    assert coating_profile.display_name in result.summary


@pytest.mark.unit
def test_calculate_panel_area() -> None:
    """Panel area is width multiplied by height, rounded to four decimals."""
    assert calculate_panel_area(2.5, 1.8) == 4.5


@pytest.mark.unit
def test_waste_mass_is_eight_percent_of_material_mass() -> None:
    """Overspray loss percentage equals 100 minus transfer efficiency."""
    result = run_simulation(
        SimulateRequest(
            material="aluminium_alloy",
            coating="anti_corrosion",
            panel_width_m=2.0,
            panel_height_m=2.0,
        )
    )
    assert result.transfer_efficiency_pct == 70
    assert result.waste_percentage == 30.0


@pytest.mark.unit
def test_waste_calculation_is_realistic() -> None:
    """Transfer-loss waste is small relative to panel mass (not flat 8%)."""
    result = run_simulation(
        SimulateRequest(
            material="aluminium_alloy",
            coating="anti_corrosion",
            panel_width_m=2.0,
            panel_height_m=1.5,
        )
    )
    assert 0.0 < result.waste_mass_kg < 1.0
    assert result.waste_volume_litres < result.coating_volume_litres


@pytest.mark.unit
def test_prep_phases_count_and_order() -> None:
    """Prep timeline has five ordered phases from degrease through cure."""
    result = run_simulation(_build_request("aluminium_alloy", "anti_corrosion"))
    assert len(result.prep_phases) == 5
    assert result.prep_phases[0].phase == "Surface degreasing"
    assert result.prep_phases[4].phase == "Cure / cool-down"


@pytest.mark.unit
def test_total_time_equals_sum_of_phases() -> None:
    """Total process time equals the sum of all phase durations."""
    result = run_simulation(_build_request("stainless_steel", "nano_ceramic"))
    phase_total = sum(p.duration_minutes for p in result.prep_phases)
    assert result.total_process_time_minutes == phase_total


@pytest.mark.unit
def test_thermal_protection_thickness_800_microns() -> None:
    """Thermal protection coating uses the 800 µm aerospace spec."""
    result = run_simulation(_build_request("aluminium_alloy", "thermal_protection"))
    assert result.coating_thickness_microns == 800


@pytest.mark.unit
def test_transfer_efficiency_fields_present() -> None:
    """Anti-corrosion exposes MIL spec and 70% transfer efficiency."""
    result = run_simulation(_build_request("aluminium_alloy", "anti_corrosion"))
    assert result.transfer_efficiency_pct == 70
    assert result.coating_standard == "MIL-PRF-85285"


@pytest.mark.unit
@pytest.mark.parametrize("coating", COATINGS)
def test_coating_specs_across_all_coatings(coating: CoatingType) -> None:
    """Every coating has valid transfer efficiency, coats, and five phases."""
    result = run_simulation(_build_request("carbon_composite", coating))
    assert result.transfer_efficiency_pct in (65, 70, 75)
    assert result.number_of_coats >= 2
    assert len(result.prep_phases) == 5


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
    coating_profile = COATING_PROFILES[coating]

    assert data["material"] == material
    assert data["coating"] == coating
    assert data["panel_area_sqm"] == PANEL_AREA_SQM
    assert data["waste_percentage"] == 100 - coating_profile.transfer_efficiency_pct
    assert data["total_process_time_minutes"] == sum(
        p["duration_minutes"] for p in data["prep_phases"]
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


# ── Database integration tests ────────────────────────────────────────────────────


@pytest.mark.integration
async def test_list_simulations_empty(client: AsyncClient) -> None:
    """GET /api/v1/simulations returns an empty list when no runs exist."""
    response = await client.get("/api/v1/simulations")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
async def test_list_and_get_simulation_by_id(client: AsyncClient) -> None:
    """POST saves a run; list and get-by-id return the persisted record."""
    post_response = await client.post("/api/v1/simulate", json=SIMULATE_PAYLOAD)
    assert post_response.status_code == 200

    list_response = await client.get("/api/v1/simulations")
    assert list_response.status_code == 200
    records = list_response.json()
    assert len(records) == 1
    assert records[0]["material"] == "aluminium_alloy"
    assert records[0]["coating"] == "anti_corrosion"
    assert records[0]["coating_thickness_microns"] == 180

    record_id = records[0]["id"]
    get_response = await client.get(f"/api/v1/simulations/{record_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == record_id
    assert get_response.json()["panel_area_sqm"] == PANEL_AREA_SQM


@pytest.mark.integration
async def test_get_simulation_not_found(client: AsyncClient) -> None:
    """GET /api/v1/simulations/{id} returns 404 for a missing record."""
    response = await client.get("/api/v1/simulations/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Simulation not found"
