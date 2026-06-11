"""Parallel-key check (clavette parallèle, ISO 773).

A parallel key transmits torque Mt between a shaft (diameter d) and a hub.
Two criteria are checked:

    1. Shear (cisaillement):
           τ = 2·Mt / (d · b · l_active)         ≤ Re_shear
       with Re_shear = Re_shaft / √3 (Von Mises shear yield).
    2. Bearing on flanks (matage):
           σ_m = 4·Mt / (d · h · l_active)       ≤ σ_m_admissible
       σ_m_admissible depends on the weakest material in contact
       (typically the hub).

`l_active = l_total − b` for a rounded-end key (the rounded portion does
not carry load).

Standard cross-sections (b, h) come from ISO 773; the helper
`select_iso_key_section` returns (b, h) for a given shaft diameter.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .advisor import Advice, generate_key_advice
from .beam import VerdictThresholds, verdict
from .materials import Material


# --------------------------------------------------------------------------- #
# Hub material — drives the admissible bearing stress                          #
# --------------------------------------------------------------------------- #
class HubMaterial(str, Enum):
    STEEL = "steel"
    CAST_IRON = "cast_iron"
    ALUMINUM = "aluminum"


HUB_BEARING_STRESS_PA: dict[HubMaterial, float] = {
    HubMaterial.STEEL: 150e6,
    HubMaterial.CAST_IRON: 80e6,
    HubMaterial.ALUMINUM: 60e6,
}


# --------------------------------------------------------------------------- #
# ISO 773 cross-section table — (d_min, d_max, b_mm, h_mm)                     #
#                                                                              #
# Convention: select the first row where d_mm ≤ d_max. So a diameter exactly   #
# on the upper bound stays in the lower bracket.                               #
# --------------------------------------------------------------------------- #
ISO_773_TABLE: list[tuple[float, float, float, float]] = [
    (6,  8,   2,  2),
    (8,  10,  3,  3),
    (10, 12,  4,  4),
    (12, 17,  5,  5),
    (17, 22,  6,  6),
    (22, 30,  8,  7),
    (30, 38, 10,  8),
    (38, 44, 12,  8),
    (44, 50, 14,  9),
    (50, 58, 16, 10),
    (58, 65, 18, 11),
    (65, 75, 20, 12),
]


def select_iso_key_section(d_mm: float) -> tuple[float, float]:
    """Return (b_mm, h_mm) for the given shaft diameter (mm) per ISO 773."""
    if not math.isfinite(d_mm) or d_mm <= 0:
        raise ValueError("shaft diameter must be a finite, positive value (mm)")
    for d_min, d_max, b, h in ISO_773_TABLE:
        if d_mm <= d_max:
            if d_mm >= d_min:
                return b, h
            raise ValueError(
                f"shaft diameter {d_mm} mm is below the ISO 773 range "
                f"(minimum {ISO_773_TABLE[0][0]} mm)"
            )
    raise ValueError(
        f"shaft diameter {d_mm} mm is above the ISO 773 range "
        f"(maximum {ISO_773_TABLE[-1][1]} mm)"
    )


# --------------------------------------------------------------------------- #
# Models                                                                       #
# --------------------------------------------------------------------------- #
class KeySection(BaseModel):
    """Parallel key cross-section + total length, in SI units (m)."""

    model_config = ConfigDict(frozen=True)

    b: float = Field(..., gt=0, description="Key width b, m")
    h: float = Field(..., gt=0, description="Key height h, m")
    l_total: float = Field(..., gt=0, description="Total key length, m")

    @model_validator(mode="after")
    def _active_length_positive(self) -> "KeySection":
        if self.l_total <= self.b:
            raise ValueError(
                f"l_total ({self.l_total} m) must be > b ({self.b} m): the "
                "active length l_active = l_total − b would be ≤ 0."
            )
        return self

    @property
    def l_active(self) -> float:
        return self.l_total - self.b


class KeyResult(BaseModel):
    """Output of `calculate_key` (SI). Presentation layer converts to MPa/mm."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    shaft_diameter_m: float
    Mt_Nm: float
    section: KeySection
    hub_material: HubMaterial
    tau_Pa: float                # shear stress
    sigma_m_Pa: float            # bearing stress
    Re_shear_Pa: float           # = material_shaft.Re / sqrt(3)
    sigma_m_adm_Pa: float        # admissible bearing stress for the hub material
    Cs_shear: float
    Cs_bearing: float
    Cs: float                    # = min(Cs_shear, Cs_bearing)
    limiting_criterion: str      # "cisaillement" | "matage"
    verdict: str
    advice: Advice


# --------------------------------------------------------------------------- #
# Calculation                                                                  #
# --------------------------------------------------------------------------- #
def calculate_key(
    shaft_diameter_m: float,
    Mt_Nm: float,
    material_shaft: Material,
    hub_material: HubMaterial,
    l_total_m: float,
    key_section: Optional[KeySection] = None,
    thresholds: VerdictThresholds = VerdictThresholds(),
) -> KeyResult:
    """Verify a parallel key under torque Mt.

    Parameters
    ----------
    shaft_diameter_m : float
        Shaft diameter (m). Used to scale the lever arm AND, if
        `key_section` is None, to pick (b, h) per ISO 773.
    Mt_Nm : float
        Torque to transmit (N·m, ≥ 0). Must be > 0.
    material_shaft : Material
        Shaft material — its Re drives the shear admissible (Re/√3).
    hub_material : HubMaterial
        Determines σ_m_admissible.
    l_total_m : float
        Total key length (m). Only used if `key_section` is None.
    key_section : KeySection, optional
        Explicit section override. If given, l_total_m is ignored.
    """
    if not math.isfinite(shaft_diameter_m) or shaft_diameter_m <= 0:
        raise ValueError("shaft_diameter_m must be > 0")
    if not math.isfinite(Mt_Nm) or Mt_Nm <= 0:
        raise ValueError("Mt_Nm must be a finite value > 0")

    if key_section is None:
        b_mm, h_mm = select_iso_key_section(shaft_diameter_m * 1e3)
        section = KeySection(
            b=b_mm * 1e-3,
            h=h_mm * 1e-3,
            l_total=l_total_m,
        )
    else:
        section = key_section

    d = shaft_diameter_m
    b = section.b
    h = section.h
    l_active = section.l_active

    tau = 2.0 * Mt_Nm / (d * b * l_active)
    sigma_m = 4.0 * Mt_Nm / (d * h * l_active)

    Re_shear = material_shaft.Re / math.sqrt(3.0)
    sigma_m_adm = HUB_BEARING_STRESS_PA[hub_material]

    cs_shear = Re_shear / tau if tau > 0 else float("inf")
    cs_bearing = sigma_m_adm / sigma_m if sigma_m > 0 else float("inf")
    cs_global = min(cs_shear, cs_bearing)
    limiting = "cisaillement" if cs_shear <= cs_bearing else "matage"
    v = verdict(cs_global, thresholds)
    advice = generate_key_advice(
        material_shaft=material_shaft,
        hub_material=hub_material,
        tau_Pa=tau,
        sigma_m_Pa=sigma_m,
        Re_shear_Pa=Re_shear,
        sigma_m_adm_Pa=sigma_m_adm,
        cs_shear=cs_shear,
        cs_bearing=cs_bearing,
        cs_global=cs_global,
        limiting=limiting,
        verdict_str=v,
    )

    return KeyResult(
        shaft_diameter_m=shaft_diameter_m,
        Mt_Nm=Mt_Nm,
        section=section,
        hub_material=hub_material,
        tau_Pa=tau,
        sigma_m_Pa=sigma_m,
        Re_shear_Pa=Re_shear,
        sigma_m_adm_Pa=sigma_m_adm,
        Cs_shear=cs_shear,
        Cs_bearing=cs_bearing,
        Cs=cs_global,
        limiting_criterion=limiting,
        verdict=v,
        advice=advice,
    )


# --------------------------------------------------------------------------- #
# Optimization                                                                 #
# --------------------------------------------------------------------------- #
from dataclasses import dataclass


@dataclass(frozen=True)
class KeyOptimizationResult:
    found: bool
    l_total_optimal_m: Optional[float]
    result: Optional[KeyResult]
    target_safety_factor: float
    l_min_m: float
    l_max_m: float
    step_m: float
    candidates_evaluated: int


def optimize_key(
    shaft_diameter_m: float,
    Mt_Nm: float,
    material_shaft: Material,
    hub_material: HubMaterial,
    target_cs: float,
    l_min_mm: Optional[float] = None,
    l_max_mm: float = 300.0,
    step_mm: float = 1.0,
) -> KeyOptimizationResult:
    """Find the smallest key length (l_total) satisfying both criteria.

    The cross-section (b, h) is auto-selected from ISO 773 based on the
    shaft diameter. The search range defaults to (b + 5 mm) to l_max_mm.
    """
    if target_cs <= 0:
        raise ValueError("target_cs must be > 0")
    if step_mm <= 0:
        raise ValueError("step_mm must be > 0")

    b_mm, h_mm = select_iso_key_section(shaft_diameter_m * 1e3)
    lo = (b_mm + 5.0) if l_min_mm is None else l_min_mm
    if lo <= b_mm:
        raise ValueError(
            f"l_min_mm ({lo}) must be > b ({b_mm}) so l_active > 0"
        )
    if l_max_mm <= lo:
        raise ValueError("l_max_mm must be > l_min_mm")

    candidates_count = 0
    l_mm = lo
    while l_mm <= l_max_mm + 1e-9:
        candidates_count += 1
        section = KeySection(
            b=b_mm * 1e-3,
            h=h_mm * 1e-3,
            l_total=l_mm * 1e-3,
        )
        res = calculate_key(
            shaft_diameter_m=shaft_diameter_m,
            Mt_Nm=Mt_Nm,
            material_shaft=material_shaft,
            hub_material=hub_material,
            l_total_m=l_mm * 1e-3,
            key_section=section,
        )
        if res.Cs >= target_cs:
            return KeyOptimizationResult(
                found=True,
                l_total_optimal_m=l_mm * 1e-3,
                result=res,
                target_safety_factor=target_cs,
                l_min_m=lo * 1e-3,
                l_max_m=l_max_mm * 1e-3,
                step_m=step_mm * 1e-3,
                candidates_evaluated=candidates_count,
            )
        l_mm += step_mm

    return KeyOptimizationResult(
        found=False,
        l_total_optimal_m=None,
        result=None,
        target_safety_factor=target_cs,
        l_min_m=lo * 1e-3,
        l_max_m=l_max_mm * 1e-3,
        step_m=step_mm * 1e-3,
        candidates_evaluated=candidates_count,
    )
