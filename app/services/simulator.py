"""Pure simulation logic for RocketPrep material prep and coating workflows."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import (
    CoatingType,
    MaterialType,
    PrepPhase,
    SimulateRequest,
    SimulateResponse,
)
from app.models.simulation_record import SimulationRecord

STRUCTURAL_PANEL_THICKNESS_M = 0.003


@dataclass(frozen=True)
class MaterialProfile:
    """Aerospace material preparation characteristics."""

    display_name: str
    density_kg_m3: float
    degrease_minutes: int
    abrasion_minutes_per_m2: float
    masking_minutes: int
    notes: str


@dataclass(frozen=True)
class CoatingProfile:
    """Aerospace protective coating application characteristics."""

    display_name: str
    coating_family: str
    coating_standard: str
    thickness_microns: int
    number_of_coats: int
    flash_time_minutes: int
    transfer_efficiency_pct: int
    coating_density_kg_l: float
    spray_rate_m2_per_minute: float
    efficiency_multiplier: float
    cure_minutes: int
    cure_description: str


MATERIAL_PROFILES: dict[MaterialType, MaterialProfile] = {
    "aluminium_alloy": MaterialProfile(
        display_name="Aluminium Alloy",
        density_kg_m3=2700.0,
        degrease_minutes=20,
        abrasion_minutes_per_m2=4.0,
        masking_minutes=15,
        notes="Requires conversion coating or anodisation pre-primer",
    ),
    "stainless_steel": MaterialProfile(
        display_name="Stainless Steel",
        density_kg_m3=7900.0,
        degrease_minutes=25,
        abrasion_minutes_per_m2=6.0,
        masking_minutes=20,
        notes="Requires electrochemical degreasing for zero-contaminant surface",
    ),
    "carbon_composite": MaterialProfile(
        display_name="Carbon Composite",
        density_kg_m3=1600.0,
        degrease_minutes=30,
        abrasion_minutes_per_m2=5.0,
        masking_minutes=25,
        notes="Specialised epoxy primer required; solvent absorption risk",
    ),
    "stainless_steel_starship": MaterialProfile(
        display_name="Stainless Steel (Starship)",
        density_kg_m3=7900.0,
        degrease_minutes=18,
        abrasion_minutes_per_m2=5.0,
        masking_minutes=18,
        notes=(
            "304L electro-polished SS; SpaceX Starship heritage. "
            "Lower degrease time: electro-polishing pre-cleans surface."
        ),
    ),
}

COATING_PROFILES: dict[CoatingType, CoatingProfile] = {
    "anti_corrosion": CoatingProfile(
        display_name="Anti-Corrosion",
        coating_family="Polyurethane Topcoat",
        coating_standard="MIL-PRF-85285",
        thickness_microns=180,
        number_of_coats=3,
        flash_time_minutes=8,
        transfer_efficiency_pct=70,
        coating_density_kg_l=1.3,
        spray_rate_m2_per_minute=3.5,
        efficiency_multiplier=1.0,   # baseline
        cure_minutes=60,
        cure_description="60 min initial set; full cure 24 hr ambient temperature",
    ),
    "thermal_protection": CoatingProfile(
        display_name="Thermal Protection",
        coating_family="Ablative Phenolic / Silicone Resin",
        coating_standard="MIL-PRF-14105E",
        thickness_microns=800,
        number_of_coats=4,
        flash_time_minutes=18,
        transfer_efficiency_pct=70,
        coating_density_kg_l=1.55,
        spray_rate_m2_per_minute=1.8,
        efficiency_multiplier=1.45,  # slowest — ablative build-up
        cure_minutes=180,
        cure_description="3 hr elevated-temperature cure (80-120 °C)",
    ),
    "nano_ceramic": CoatingProfile(
        display_name="Nano-Ceramic (UHTC)",
        coating_family="Ultra-High Temperature Ceramic",
        coating_standard="UHTC Plasma-Spray (ZrB\u2082/SiC)",
        thickness_microns=250,
        number_of_coats=2,
        flash_time_minutes=0,
        transfer_efficiency_pct=75,
        coating_density_kg_l=2.1,
        spray_rate_m2_per_minute=1.2,
        efficiency_multiplier=1.25,  # UHTC plasma-spray overhead
        cure_minutes=90,
        cure_description=(
            "90 min controlled cool-down to prevent thermal shock cracking"
        ),
    ),
}


def calculate_panel_area(width_m: float, height_m: float) -> float:
    """Return panel surface area in square metres."""
    return round(width_m * height_m, 4)


def calculate_prep_time(material: MaterialType, area_sqm: float) -> int:
    """Return surface prep time (degrease + abrasion + masking) in minutes."""
    profile = MATERIAL_PROFILES[material]
    degrease = 15 + round(4 * (area_sqm**0.55))
    abrasion = 45 + round(8 * (area_sqm**0.6))
    masking = 12 + round(6 * (area_sqm**0.55))
    return degrease + abrasion + masking


def calculate_coating_cure_time(coating: CoatingType, area_sqm: float) -> int:
    """Return final cure / cool-down time in minutes (fixed by chemistry)."""
    _ = area_sqm
    return COATING_PROFILES[coating].cure_minutes


def calculate_application_time(coating: CoatingType, area_sqm: float) -> int:
    """Return coating application time using team-rate formula.

    Effective spray rate: 12 m²/min across the full team.
    A per-coating efficiency_multiplier captures ablative build-up
    and plasma-spray overhead (anti_corrosion=1.0, thermal=1.45, nano=1.25).
    """
    profile = COATING_PROFILES[coating]
    return 25 + round((area_sqm / 12) * profile.efficiency_multiplier)


def calculate_material_mass(material: MaterialType, area_sqm: float) -> float:
    """Return estimated structural panel mass in kilograms (3 mm thickness)."""
    profile = MATERIAL_PROFILES[material]
    return round(
        area_sqm * profile.density_kg_m3 * STRUCTURAL_PANEL_THICKNESS_M,
        2,
    )


def calculate_coating_volumes(
    area_sqm: float,
    thickness_microns: int,
    transfer_efficiency_pct: int,
    coating_density_kg_l: float,
) -> tuple[float, float, float, float]:
    """
    Return coating volume, waste volume, waste mass, and waste percentage.

    Waste is transfer-loss overspray, not a flat panel-mass fraction.
    """
    coating_volume_m3 = area_sqm * (thickness_microns / 1_000_000)
    coating_volume_litres = round(coating_volume_m3 * 1000, 2)
    total_sprayed_litres = coating_volume_litres / (transfer_efficiency_pct / 100)
    waste_volume_litres = round(total_sprayed_litres - coating_volume_litres, 2)
    waste_mass_kg = round(waste_volume_litres * coating_density_kg_l, 2)
    waste_percentage = float(100 - transfer_efficiency_pct)
    return coating_volume_litres, waste_volume_litres, waste_mass_kg, waste_percentage


def build_prep_phases(
    material: MaterialProfile,
    coating: CoatingProfile,
    area_sqm: float,
    phase_durations: tuple[int, int, int, int, int],
) -> list[PrepPhase]:
    """Build the ordered five-phase preparation and coating timeline."""
    phase1, phase2, phase3, phase4, phase5 = phase_durations

    return [
        PrepPhase(
            phase="Surface degreasing",
            duration_minutes=phase1,
            description=(
                "Solvent wipe with IPA/acetone; remove all contamination per "
                "NASA zero-molecular cleanliness standard (scaled to panel area)"
            ),
        ),
        PrepPhase(
            phase="Mechanical abrasion",
            duration_minutes=phase2,
            description=(
                "Sand to Ra 1.5-3.0 um surface roughness for mechanical adhesion "
                "tooth; tack-rag all dust before coating"
            ),
        ),
        PrepPhase(
            phase="Precision masking",
            duration_minutes=phase3,
            description=(
                "Kapton polyimide tape over sensors, grounding points, separation "
                "bolts, and sealing flanges (scaled to panel area)"
            ),
        ),
        PrepPhase(
            phase="Coating application",
            duration_minutes=phase4,
            description=(
                f"{coating.number_of_coats} coats at {coating.thickness_microns} \u00b5m "
                f"total; {coating.flash_time_minutes} min flash time between coats; "
                f"{coating.transfer_efficiency_pct}% transfer efficiency "
                f"({coating.coating_standard})"
            ),
        ),
        PrepPhase(
            phase="Cure / cool-down",
            duration_minutes=phase5,
            description=coating.cure_description,
        ),
    ]


def run_simulation(request: SimulateRequest) -> SimulateResponse:
    """
    Execute a full material preparation and coating simulation.

    Uses aerospace-accurate material profiles, coating specs, phased prep
    timeline, and transfer-efficiency-based waste calculation.
    Degreasing and masking phases scale dynamically with panel area.
    """
    material = MATERIAL_PROFILES[request.material]
    coating = COATING_PROFILES[request.coating]

    area_sqm = calculate_panel_area(request.panel_width_m, request.panel_height_m)

    # ------------------------------------------------------------------
    # Phase durations
    # ------------------------------------------------------------------
    # Phase 1: surface degreasing  — 15 min base + sub-linear area term
    phase1 = 15 + round(4 * (area_sqm**0.55))
    # Phase 2: mechanical abrasion — 45 min base + sub-linear area term
    #          (strong diminishing returns; does NOT dominate large panels)
    phase2 = 45 + round(8 * (area_sqm**0.6))
    # Phase 3: precision masking   — 12 min base + sub-linear area term
    phase3 = 12 + round(6 * (area_sqm**0.55))
    # Phase 4: coating application — team rate 12 m²/min with coating multiplier
    phase4 = 25 + round((area_sqm / 12) * coating.efficiency_multiplier)
    # Phase 5: cure / cool-down   — fixed by coating chemistry, not area
    phase5 = coating.cure_minutes

    # ------------------------------------------------------------------
    # Global bounds  (min 90 min, max 540 min / 9 hr)
    # Apply ceiling by trimming the application phase so the invariant
    # total == sum(phases) is always satisfied.
    # ------------------------------------------------------------------
    MIN_TOTAL = 90
    MAX_TOTAL = 540
    raw_total = phase1 + phase2 + phase3 + phase4 + phase5
    if raw_total < MIN_TOTAL:
        # Pad the application phase up to the floor
        phase4 += MIN_TOTAL - raw_total
    elif raw_total > MAX_TOTAL:
        # Trim the application phase down to the ceiling
        excess = raw_total - MAX_TOTAL
        phase4 = max(0, phase4 - excess)

    prep_phases = build_prep_phases(
        material, coating, area_sqm, (phase1, phase2, phase3, phase4, phase5)
    )

    prep_time_minutes = phase1 + phase2 + phase3
    coating_cure_minutes = phase5
    total_process_time_minutes = phase1 + phase2 + phase3 + phase4 + phase5

    coating_volume_litres, waste_volume_litres, waste_mass_kg, waste_percentage = (
        calculate_coating_volumes(
            area_sqm,
            coating.thickness_microns,
            coating.transfer_efficiency_pct,
            coating.coating_density_kg_l,
        )
    )

    estimated_material_mass_kg = calculate_material_mass(request.material, area_sqm)

    phase_summary = (
        f"5 phases: degrease {phase1}min \u2192 abrasion {phase2}min \u2192 "
        f"masking {phase3}min \u2192 {coating.number_of_coats} coats {phase4}min \u2192 "
        f"cure {phase5}min"
    )

    summary = (
        f"Prepared {area_sqm:.2f} m\u00b2 {material.display_name} panel with "
        f"{coating.display_name} coating ({coating.thickness_microns} \u00b5m)."
    )

    return SimulateResponse(
        material=request.material,
        material_display_name=material.display_name,
        coating=request.coating,
        coating_display_name=coating.display_name,
        panel_width_m=request.panel_width_m,
        panel_height_m=request.panel_height_m,
        panel_area_sqm=area_sqm,
        prep_time_minutes=prep_time_minutes,
        coating_thickness_microns=coating.thickness_microns,
        coating_cure_minutes=coating_cure_minutes,
        total_process_time_minutes=total_process_time_minutes,
        estimated_material_mass_kg=estimated_material_mass_kg,
        waste_percentage=waste_percentage,
        waste_mass_kg=waste_mass_kg,
        summary=summary,
        coating_family=coating.coating_family,
        coating_standard=coating.coating_standard,
        number_of_coats=coating.number_of_coats,
        flash_time_minutes=coating.flash_time_minutes,
        transfer_efficiency_pct=coating.transfer_efficiency_pct,
        coating_volume_litres=coating_volume_litres,
        waste_volume_litres=waste_volume_litres,
        prep_phases=prep_phases,
        phase_summary=phase_summary,
    )


async def save_simulation(
    db: AsyncSession,
    result: SimulateResponse,
) -> SimulationRecord:
    """Persist a simulation result to the database."""
    record = SimulationRecord(
        material=result.material,
        coating=result.coating,
        panel_width_m=result.panel_width_m,
        panel_height_m=result.panel_height_m,
        panel_area_sqm=result.panel_area_sqm,
        prep_time_minutes=result.prep_time_minutes,
        coating_thickness_microns=result.coating_thickness_microns,
        total_process_time_minutes=result.total_process_time_minutes,
        waste_percentage=result.waste_percentage,
        waste_mass_kg=result.waste_mass_kg,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_simulations(db: AsyncSession) -> list[SimulationRecord]:
    """Return all stored simulation runs, newest first."""
    result = await db.execute(
        select(SimulationRecord).order_by(SimulationRecord.created_at.desc())
    )
    return list(result.scalars().all())


async def get_simulation(db: AsyncSession, record_id: int) -> SimulationRecord | None:
    """Return a single simulation run by id, or None if not found."""
    return await db.get(SimulationRecord, record_id)
