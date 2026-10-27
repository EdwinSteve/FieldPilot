"""Unit conversions shared by the simulator and the safety rules (D015)."""


def pct_of_field_capacity(volumetric_pct: float, field_capacity_vwc: float) -> float:
    """Convert volumetric water content (%) into percent of field capacity.

    Sensors report volumetric content; safety limits (e.g. 85 %) are
    expressed relative to field capacity. Keeping the conversion in one
    place prevents comparing a raw sensor value against a relative limit.
    """
    if field_capacity_vwc <= 0:
        raise ValueError("field capacity must be positive")
    return volumetric_pct / field_capacity_vwc * 100
