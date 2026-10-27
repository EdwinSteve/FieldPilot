"""Root-zone water balance as pure functions.

A deliberately simple bucket model, enough to make irrigation decisions
visible in the demo. Not an agronomic reference (see README limitations).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SoilParams:
    """Soil of one zone. Water contents are volumetric percentages."""

    root_depth_mm: float = 300.0
    field_capacity_vwc: float = 32.0
    wilting_point_vwc: float = 12.0
    saturation_vwc: float = 45.0
    drainage_per_day: float = 0.5  # fraction of the excess above field capacity

    def __post_init__(self) -> None:
        ordered = 0 < self.wilting_point_vwc < self.field_capacity_vwc < self.saturation_vwc
        if not ordered or self.root_depth_mm <= 0 or not 0 <= self.drainage_per_day <= 1:
            raise ValueError(f"inconsistent soil parameters: {self}")

    def water_mm(self, vwc: float) -> float:
        """Water stored in the root zone for a volumetric content."""
        return vwc / 100 * self.root_depth_mm

    def vwc(self, water_mm: float) -> float:
        """Volumetric content for an amount of stored water."""
        return water_mm / self.root_depth_mm * 100


@dataclass(frozen=True)
class WaterInputs:
    """Water entering and leaving during one interval, in mm."""

    rain_mm: float
    irrigation_mm: float
    et0_mm: float
    crop_coefficient: float
    interval_days: float


@dataclass(frozen=True)
class WaterStep:
    vwc: float
    et_mm: float
    drained_mm: float
    runoff_mm: float


def crop_et_mm(et0_mm: float, crop_coefficient: float) -> float:
    """Crop evapotranspiration: reference ET0 scaled by the crop coefficient Kc."""
    return et0_mm * crop_coefficient


def step_water_balance(vwc: float, inputs: WaterInputs, soil: SoilParams) -> WaterStep:
    """Advance the root-zone water content by one interval (explicit Euler).

    Drainage is computed from the content at the start of the interval, so
    water added during the interval drains in later intervals, never
    instantly. Content never drops below the wilting point (ET stops) and
    never exceeds saturation (the excess runs off).
    """
    water = soil.water_mm(vwc)
    excess = max(water - soil.water_mm(soil.field_capacity_vwc), 0.0)
    drained = excess * min(soil.drainage_per_day * inputs.interval_days, 1.0)

    floor = soil.water_mm(soil.wilting_point_vwc)
    available_for_et = max(water - drained + inputs.rain_mm + inputs.irrigation_mm - floor, 0.0)
    et = min(crop_et_mm(inputs.et0_mm, inputs.crop_coefficient), available_for_et)

    water = water - drained - et + inputs.rain_mm + inputs.irrigation_mm
    ceiling = soil.water_mm(soil.saturation_vwc)
    runoff = max(water - ceiling, 0.0)
    water = max(min(water, ceiling), floor)

    return WaterStep(vwc=soil.vwc(water), et_mm=et, drained_mm=drained, runoff_mm=runoff)
