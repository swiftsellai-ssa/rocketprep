"""Pydantic v2 request and response schemas for the RocketPrep simulator."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MaterialType = Literal["aluminium_alloy", "stainless_steel", "carbon_composite"]
CoatingType = Literal["anti_corrosion", "thermal_protection", "nano_ceramic"]


class SimulateRequest(BaseModel):
    """Input parameters for a material preparation and coating simulation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "material": "aluminium_alloy",
                    "coating": "anti_corrosion",
                    "panel_width_m": 2.5,
                    "panel_height_m": 1.8,
                }
            ]
        }
    )

    material: MaterialType = Field(
        ...,
        description="Aerospace panel material to prepare",
        examples=["aluminium_alloy"],
    )
    coating: CoatingType = Field(
        ...,
        description="Protective coating to apply after preparation",
        examples=["anti_corrosion"],
    )
    panel_width_m: float = Field(
        ...,
        gt=0,
        description="Panel width in metres",
        examples=[2.5],
    )
    panel_height_m: float = Field(
        ...,
        gt=0,
        description="Panel height in metres",
        examples=[1.8],
    )

    @field_validator("panel_width_m", "panel_height_m")
    @classmethod
    def dimensions_must_be_positive(cls, value: float) -> float:
        """Reject non-positive panel dimensions."""
        if value <= 0:
            msg = "Panel dimensions must be greater than zero"
            raise ValueError(msg)
        return value


class PrepPhase(BaseModel):
    """A single step in the material preparation and coating timeline."""

    phase: str = Field(..., description="Phase name")
    duration_minutes: int = Field(..., description="Duration of this phase in minutes")
    description: str = Field(..., description="Detailed phase description")


class SimulateResponse(BaseModel):
    """Simulation results for material prep and protective coating."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "material": "aluminium_alloy",
                    "material_display_name": "Aluminium Alloy",
                    "coating": "anti_corrosion",
                    "coating_display_name": "Anti-Corrosion",
                    "panel_width_m": 2.5,
                    "panel_height_m": 1.8,
                    "panel_area_sqm": 4.5,
                    "prep_time_minutes": 51,
                    "coating_thickness_microns": 180,
                    "coating_cure_minutes": 60,
                    "total_process_time_minutes": 120,
                    "estimated_material_mass_kg": 0.04,
                    "waste_percentage": 30.0,
                    "waste_mass_kg": 0.16,
                    "coating_family": "Polyurethane Topcoat",
                    "coating_standard": "MIL-PRF-85285",
                    "number_of_coats": 3,
                    "flash_time_minutes": 8,
                    "transfer_efficiency_pct": 70,
                    "coating_volume_litres": 0.81,
                    "waste_volume_litres": 0.35,
                    "prep_phases": [],
                    "phase_summary": "5 phases: degrease 20min → abrasion 18min → masking 15min → 3 coats 17min → cure 60min",
                    "summary": (
                        "Prepared 4.50 m² Aluminium Alloy panel with "
                        "Anti-Corrosion coating (180 µm)."
                    ),
                }
            ]
        }
    )

    material: MaterialType = Field(
        ...,
        description="Material used in the simulation",
    )
    material_display_name: str = Field(
        ...,
        description="Human-readable material name",
    )
    coating: CoatingType = Field(
        ...,
        description="Coating applied in the simulation",
    )
    coating_display_name: str = Field(
        ...,
        description="Human-readable coating name",
    )
    panel_width_m: float = Field(
        ...,
        description="Panel width in metres",
    )
    panel_height_m: float = Field(
        ...,
        description="Panel height in metres",
    )
    panel_area_sqm: float = Field(
        ...,
        description="Calculated panel surface area in square metres",
    )
    prep_time_minutes: int = Field(
        ...,
        description="Surface prep time (degrease + abrasion + masking) in minutes",
    )
    coating_thickness_microns: int = Field(
        ...,
        description="Target coating thickness in microns",
    )
    coating_cure_minutes: int = Field(
        ...,
        description="Final cure / cool-down time in minutes",
    )
    total_process_time_minutes: int = Field(
        ...,
        description="Combined time for all five process phases in minutes",
    )
    estimated_material_mass_kg: float = Field(
        ...,
        description="Estimated panel material mass in kilograms (3 mm panel)",
    )
    waste_percentage: float = Field(
        ...,
        description="Overspray loss percentage (100 - transfer efficiency)",
    )
    waste_mass_kg: float = Field(
        ...,
        description="Coating waste mass in kilograms from transfer loss",
    )
    summary: str = Field(
        ...,
        description="Plain-language summary of the simulation outcome",
    )
    coating_family: str = Field(
        ...,
        description="Coating chemistry family (e.g. Polyurethane Topcoat)",
    )
    coating_standard: str = Field(
        ...,
        description="Military or industry specification reference",
    )
    number_of_coats: int = Field(
        ...,
        description="Number of coating passes applied",
    )
    flash_time_minutes: int = Field(
        ...,
        description="Flash time between coats in minutes",
    )
    transfer_efficiency_pct: int = Field(
        ...,
        description="Spray transfer efficiency percentage",
    )
    coating_volume_litres: float = Field(
        ...,
        description="Target coating volume on panel in litres",
    )
    waste_volume_litres: float = Field(
        ...,
        description="Overspray waste volume in litres",
    )
    prep_phases: list[PrepPhase] = Field(
        ...,
        description="Ordered breakdown of all process phases",
    )
    phase_summary: str = Field(
        ...,
        description="One-line human-readable phase timeline",
    )


class SimulationRecordResponse(BaseModel):
    """Persisted simulation run returned from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Database primary key")
    material: MaterialType = Field(..., description="Material used in the simulation")
    coating: CoatingType = Field(..., description="Coating applied in the simulation")
    panel_width_m: float = Field(..., description="Panel width in metres")
    panel_height_m: float = Field(..., description="Panel height in metres")
    panel_area_sqm: float = Field(
        ...,
        description="Calculated panel surface area in square metres",
    )
    prep_time_minutes: int = Field(
        ...,
        description="Material surface preparation time in minutes",
    )
    coating_thickness_microns: int = Field(
        ...,
        description="Target coating thickness in microns",
    )
    total_process_time_minutes: int = Field(
        ...,
        description="Combined prep and coating process time in minutes",
    )
    waste_percentage: float = Field(
        ...,
        description="Material waste percentage",
    )
    waste_mass_kg: float = Field(
        ...,
        description="Estimated waste mass in kilograms",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the simulation was stored",
    )
