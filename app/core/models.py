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
                    "prep_time_minutes": 81,
                    "coating_thickness_microns": 50,
                    "coating_cure_minutes": 30,
                    "total_process_time_minutes": 111,
                    "estimated_material_mass_kg": 56.25,
                    "waste_percentage": 8.0,
                    "waste_mass_kg": 4.5,
                    "summary": (
                        "Prepared 4.50 m² Aluminium Alloy panel with "
                        "Anti-Corrosion coating (50 µm)."
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
        description="Material surface preparation time in minutes",
    )
    coating_thickness_microns: int = Field(
        ...,
        description="Target coating thickness in microns",
    )
    coating_cure_minutes: int = Field(
        ...,
        description="Coating application and cure time in minutes",
    )
    total_process_time_minutes: int = Field(
        ...,
        description="Combined prep and coating process time in minutes",
    )
    estimated_material_mass_kg: float = Field(
        ...,
        description="Estimated panel material mass before waste in kilograms",
    )
    waste_percentage: float = Field(
        ...,
        description="Material waste percentage (fixed at ~8%)",
    )
    waste_mass_kg: float = Field(
        ...,
        description="Estimated waste mass in kilograms",
    )
    summary: str = Field(
        ...,
        description="Plain-language summary of the simulation outcome",
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
