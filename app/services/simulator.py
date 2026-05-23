"""Pure simulation logic for RocketPrep material prep and coating workflows."""

from dataclasses import dataclass

from app.core.models import (
    CoatingType,
    MaterialType,
    SimulateRequest,
    SimulateResponse,
)

WASTE_PERCENTAGE: float = 8.0
WASTE_FRACTION: float = WASTE_PERCENTAGE / 100.0


@dataclass(frozen=True)
class MaterialProfile:
    """Physical and timing characteristics for an aerospace material."""

    display_name: str
    base_prep_minutes: int
    minutes_per_sqm: float
    mass_kg_per_sqm: float


@dataclass(frozen=True)
class CoatingProfile:
    """Thickness and cure characteristics for a protective coating."""

    display_name: str
    thickness_microns: int
    base_cure_minutes: int
    minutes_per_sqm: float


MATERIAL_PROFILES: dict[MaterialType, MaterialProfile] = {
    "aluminium_alloy": MaterialProfile(
        display_name="Aluminium Alloy",
        base_prep_minutes=45,
        minutes_per_sqm=8.0,
        mass_kg_per_sqm=12.5,
    ),
    "stainless_steel": MaterialProfile(
        display_name="Stainless Steel",
        base_prep_minutes=60,
        minutes_per_sqm=12.0,
        mass_kg_per_sqm=28.0,
    ),
    "carbon_composite": MaterialProfile(
        display_name="Carbon Composite",
        base_prep_minutes=90,
        minutes_per_sqm=15.0,
        mass_kg_per_sqm=4.5,
    ),
}

COATING_PROFILES: dict[CoatingType, CoatingProfile] = {
    "anti_corrosion": CoatingProfile(
        display_name="Anti-Corrosion",
        thickness_microns=120,
        base_cure_minutes=30,
        minutes_per_sqm=4.0,
    ),
    "thermal_protection": CoatingProfile(
        display_name="Thermal Protection",
        thickness_microns=800,
        base_cure_minutes=75,
        minutes_per_sqm=9.0,
    ),
    "nano_ceramic": CoatingProfile(
        display_name="Nano-Ceramic",
        thickness_microns=250,
        base_cure_minutes=55,
        minutes_per_sqm=6.5,
    ),
}


def calculate_panel_area(width_m: float, height_m: float) -> float:
    """Return panel surface area in square metres."""
    return round(width_m * height_m, 4)


def calculate_prep_time(material: MaterialType, area_sqm: float) -> int:
    """Return material surface preparation time in minutes."""
    profile = MATERIAL_PROFILES[material]
    raw_minutes = profile.base_prep_minutes + (area_sqm * profile.minutes_per_sqm)
    return round(raw_minutes)


def calculate_coating_cure_time(coating: CoatingType, area_sqm: float) -> int:
    """Return coating application and cure time in minutes."""
    profile = COATING_PROFILES[coating]
    raw_minutes = profile.base_cure_minutes + (area_sqm * profile.minutes_per_sqm)
    return round(raw_minutes)


def calculate_material_mass(material: MaterialType, area_sqm: float) -> float:
    """Return estimated panel material mass in kilograms."""
    profile = MATERIAL_PROFILES[material]
    return round(area_sqm * profile.mass_kg_per_sqm, 2)


def calculate_waste_mass(material_mass_kg: float) -> float:
    """Return waste mass in kilograms at the fixed ~8% waste rate."""
    return round(material_mass_kg * WASTE_FRACTION, 2)


def run_simulation(request: SimulateRequest) -> SimulateResponse:
    """
    Execute a full material preparation and coating simulation.

    Converts panel dimensions, material choice, and coating type into
    timing, thickness, mass, and waste estimates.
    """
    material_profile = MATERIAL_PROFILES[request.material]
    coating_profile = COATING_PROFILES[request.coating]

    area_sqm = calculate_panel_area(request.panel_width_m, request.panel_height_m)
    prep_time = calculate_prep_time(request.material, area_sqm)
    coating_cure = calculate_coating_cure_time(request.coating, area_sqm)
    material_mass = calculate_material_mass(request.material, area_sqm)
    waste_mass = calculate_waste_mass(material_mass)

    summary = (
        f"Prepared {area_sqm:.2f} m² {material_profile.display_name} panel with "
        f"{coating_profile.display_name} coating "
        f"({coating_profile.thickness_microns} µm)."
    )

    return SimulateResponse(
        material=request.material,
        material_display_name=material_profile.display_name,
        coating=request.coating,
        coating_display_name=coating_profile.display_name,
        panel_width_m=request.panel_width_m,
        panel_height_m=request.panel_height_m,
        panel_area_sqm=area_sqm,
        prep_time_minutes=prep_time,
        coating_thickness_microns=coating_profile.thickness_microns,
        coating_cure_minutes=coating_cure,
        total_process_time_minutes=prep_time + coating_cure,
        estimated_material_mass_kg=material_mass,
        waste_percentage=WASTE_PERCENTAGE,
        waste_mass_kg=waste_mass,
        summary=summary,
    )
