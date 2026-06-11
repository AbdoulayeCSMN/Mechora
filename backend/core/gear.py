"""Spur gear (engrenage droit) sizing — simplified Lewis bending + Hertz contact.

This module follows the spirit of ISO 6336 (bending strength + surface
durability of cylindrical gears) but with the simplified factor set commonly
used for first-pass sizing:

    Bending (Lewis, per ISO 6336 layout):
        σ_F = (Ft · K_A · K_V / (b · m)) · Y_F

    Contact (Hertz, per ISO 6336 layout):
        σ_H = Z_E · sqrt( (Ft · K_A · K_V / (b · d1)) · (u + 1) / u )

    with:
        Ft  = 2 · Mt1 / d1                  tangential force at the pitch circle
        K_A = application factor (input)
        K_V = 1 + v / 6                     simplified dynamic factor (v in m/s)
        Y_F = Lewis form factor, interpolated from a 20° full-depth table
        Z_E = elasticity factor, derived from E and ν of both materials
        u   = z2 / z1                       gear ratio

Admissible stresses come from the material catalogue:
    σ_F_adm = material.sigma_D       (alternating bending fatigue limit)
    σ_H_adm = min(pinion, gear).sigma_H_lim   (contact/pitting fatigue limit)

These are first-pass / pedagogical estimates, not a full ISO 6336 calculation
(no K_Hβ, K_Fβ, Y_ε, Y_β, Z_ε, Z_β micro-geometry factors).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .advisor import Advice, generate_gear_advice
from .beam import VerdictThresholds, verdict
from .materials import Material


# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #
PRESSURE_ANGLE_DEG = 20.0

# Preferred ISO module series (mm) used for module-selection optimization.
ISO_MODULE_SERIES_MM: List[float] = [
    1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 25.0,
]

MIN_TEETH = 12  # below this, undercut/interference at 20° pressure angle

# Lewis form factor Y_F for 20° full-depth involute external teeth,
# interpolated by tooth count z. Standard textbook table values.
LEWIS_FORM_FACTOR_TABLE: List[tuple[int, float]] = [
    (12, 0.245), (13, 0.261), (14, 0.277), (15, 0.290), (16, 0.296),
    (17, 0.303), (18, 0.309), (19, 0.314), (20, 0.322), (22, 0.331),
    (24, 0.337), (26, 0.346), (28, 0.353), (30, 0.359), (34, 0.371),
    (38, 0.384), (43, 0.397), (50, 0.409), (60, 0.422), (75, 0.435),
    (100, 0.447), (150, 0.460), (300, 0.472), (1000, 0.484),
]


def lewis_form_factor(z: int) -> float:
    """Interpolate the Lewis form factor Y_F for `z` teeth (20° full depth)."""
    if z < LEWIS_FORM_FACTOR_TABLE[0][0]:
        raise ValueError(
            f"z={z} is below the minimum supported tooth count "
            f"({LEWIS_FORM_FACTOR_TABLE[0][0]}, interférence à 20°)"
        )
    if z >= LEWIS_FORM_FACTOR_TABLE[-1][0]:
        return LEWIS_FORM_FACTOR_TABLE[-1][1]

    for (z_lo, y_lo), (z_hi, y_hi) in zip(LEWIS_FORM_FACTOR_TABLE, LEWIS_FORM_FACTOR_TABLE[1:]):
        if z_lo <= z <= z_hi:
            if z == z_lo:
                return y_lo
            t = (z - z_lo) / (z_hi - z_lo)
            return y_lo + t * (y_hi - y_lo)

    raise AssertionError("unreachable")  # pragma: no cover


def elasticity_factor(material_a: Material, material_b: Material) -> float:
    """ISO 6336 elasticity factor Z_E (Pa^0.5), from E and ν of both flanks."""
    term = (
        (1 - material_a.poisson_ratio ** 2) / material_a.E
        + (1 - material_b.poisson_ratio ** 2) / material_b.E
    )
    return math.sqrt(1.0 / (math.pi * term))


# --------------------------------------------------------------------------- #
# Models                                                                       #
# --------------------------------------------------------------------------- #
class GearGeometry(BaseModel):
    """Spur gear pair geometry, SI units (m)."""

    model_config = ConfigDict(frozen=True)

    m: float = Field(..., gt=0, description="Module, m")
    z1: int = Field(..., ge=MIN_TEETH, description="Nombre de dents du pignon")
    z2: int = Field(..., ge=MIN_TEETH, description="Nombre de dents de la roue")
    b: float = Field(..., gt=0, description="Largeur de denture, m")

    @property
    def d1(self) -> float:
        return self.m * self.z1

    @property
    def d2(self) -> float:
        return self.m * self.z2

    @property
    def a(self) -> float:
        return (self.d1 + self.d2) / 2.0

    @property
    def u(self) -> float:
        return self.z2 / self.z1


class GearResult(BaseModel):
    """Output of `calculate_gear` (SI). Presentation layer converts to MPa/mm."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    geometry: GearGeometry
    Mt1_Nm: float
    n1_rpm: float
    Ft_N: float
    Fr_N: float
    v_m_s: float
    K_A: float
    K_V: float
    sigma_F1_Pa: float
    sigma_F2_Pa: float
    sigma_F1_adm_Pa: float
    sigma_F2_adm_Pa: float
    sigma_H_Pa: float
    sigma_H_adm_Pa: float
    Cs_F1: float
    Cs_F2: float
    Cs_H: float
    Cs: float
    limiting_criterion: str  # "flexion_pignon" | "flexion_roue" | "pression_superficielle"
    verdict: str
    advice: Advice


# --------------------------------------------------------------------------- #
# Calculation                                                                  #
# --------------------------------------------------------------------------- #
def calculate_gear(
    *,
    m_m: float,
    z1: int,
    z2: int,
    b_m: float,
    Mt1_Nm: float,
    n1_rpm: float,
    material_pinion: Material,
    material_gear: Material,
    K_A: float = 1.0,
    thresholds: VerdictThresholds = VerdictThresholds(),
) -> GearResult:
    """Verify a spur gear pair under torque Mt1 on the pinion shaft.

    Parameters
    ----------
    m_m : float
        Module, m.
    z1, z2 : int
        Tooth counts of pinion and gear (>= 12).
    b_m : float
        Face width, m.
    Mt1_Nm : float
        Torque on the pinion shaft, N·m (> 0).
    n1_rpm : float
        Pinion rotation speed, rpm (> 0).
    material_pinion, material_gear : Material
        Materials of pinion and gear (drive σ_F_adm and σ_H_adm).
    K_A : float
        Application factor (load/shock severity), default 1.0.
    """
    if not math.isfinite(m_m) or m_m <= 0:
        raise ValueError("m_m must be > 0")
    if not math.isfinite(b_m) or b_m <= 0:
        raise ValueError("b_m must be > 0")
    if not math.isfinite(Mt1_Nm) or Mt1_Nm <= 0:
        raise ValueError("Mt1_Nm must be a finite value > 0")
    if not math.isfinite(n1_rpm) or n1_rpm <= 0:
        raise ValueError("n1_rpm must be a finite value > 0")
    if not math.isfinite(K_A) or K_A <= 0:
        raise ValueError("K_A must be > 0")

    geometry = GearGeometry(m=m_m, z1=z1, z2=z2, b=b_m)
    d1, u = geometry.d1, geometry.u

    Ft = 2.0 * Mt1_Nm / d1
    Fr = Ft * math.tan(math.radians(PRESSURE_ANGLE_DEG))
    v = math.pi * d1 * n1_rpm / 60.0
    Kv = 1.0 + v / 6.0

    YF1 = lewis_form_factor(z1)
    YF2 = lewis_form_factor(z2)

    base_bending = Ft * K_A * Kv / (b_m * m_m)
    sigma_F1 = base_bending * YF1
    sigma_F2 = base_bending * YF2

    sigma_F1_adm = material_pinion.sigma_D
    sigma_F2_adm = material_gear.sigma_D
    if sigma_F1_adm is None or sigma_F2_adm is None:  # pragma: no cover - always derived
        raise ValueError("material sigma_D could not be determined")

    Z_E = elasticity_factor(material_pinion, material_gear)
    sigma_H = Z_E * math.sqrt(
        (Ft * K_A * Kv / (b_m * d1)) * ((u + 1.0) / u)
    )
    sigma_H_adm = min(material_pinion.sigma_H_lim, material_gear.sigma_H_lim)

    cs_f1 = sigma_F1_adm / sigma_F1 if sigma_F1 > 0 else float("inf")
    cs_f2 = sigma_F2_adm / sigma_F2 if sigma_F2 > 0 else float("inf")
    cs_h = sigma_H_adm / sigma_H if sigma_H > 0 else float("inf")

    cs_global = min(cs_f1, cs_f2, cs_h)
    limiting = min(
        (
            ("flexion_pignon", cs_f1),
            ("flexion_roue", cs_f2),
            ("pression_superficielle", cs_h),
        ),
        key=lambda pair: pair[1],
    )[0]

    v_str = verdict(cs_global, thresholds)
    advice = generate_gear_advice(
        sigma_F1_Pa=sigma_F1,
        sigma_F2_Pa=sigma_F2,
        sigma_F1_adm_Pa=sigma_F1_adm,
        sigma_F2_adm_Pa=sigma_F2_adm,
        sigma_H_Pa=sigma_H,
        sigma_H_adm_Pa=sigma_H_adm,
        cs_f1=cs_f1,
        cs_f2=cs_f2,
        cs_h=cs_h,
        cs_global=cs_global,
        limiting=limiting,
        verdict_str=v_str,
    )

    return GearResult(
        geometry=geometry,
        Mt1_Nm=Mt1_Nm,
        n1_rpm=n1_rpm,
        Ft_N=Ft,
        Fr_N=Fr,
        v_m_s=v,
        K_A=K_A,
        K_V=Kv,
        sigma_F1_Pa=sigma_F1,
        sigma_F2_Pa=sigma_F2,
        sigma_F1_adm_Pa=sigma_F1_adm,
        sigma_F2_adm_Pa=sigma_F2_adm,
        sigma_H_Pa=sigma_H,
        sigma_H_adm_Pa=sigma_H_adm,
        Cs_F1=cs_f1,
        Cs_F2=cs_f2,
        Cs_H=cs_h,
        Cs=cs_global,
        limiting_criterion=limiting,
        verdict=v_str,
        advice=advice,
    )


# --------------------------------------------------------------------------- #
# Optimization — module selection                                              #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GearEvaluation:
    m_mm: float
    b_mm: float
    Cs: float
    status: str  # "OK" | "insuffisant"
    limiting_criterion: str


@dataclass(frozen=True)
class GearOptimizationResult:
    found: bool
    m_optimal_mm: Optional[float]
    result: Optional[GearResult]
    target_safety_factor: float
    psi_m: float
    evaluations: List[GearEvaluation]


def optimize_gear(
    *,
    z1: int,
    z2: int,
    Mt1_Nm: float,
    n1_rpm: float,
    material_pinion: Material,
    material_gear: Material,
    target_cs: float,
    K_A: float = 1.0,
    psi_m: float = 10.0,
    module_series_mm: Optional[List[float]] = None,
) -> GearOptimizationResult:
    """Find the smallest standard module satisfying Cs >= target_cs.

    The face width is derived from the module via `b = psi_m * m`
    (psi_m is the usual b/m face-width ratio, default 10).
    """
    if target_cs <= 0:
        raise ValueError("target_cs must be > 0")
    if psi_m <= 0:
        raise ValueError("psi_m must be > 0")

    series = module_series_mm or ISO_MODULE_SERIES_MM

    evaluations: List[GearEvaluation] = []
    for m_mm in series:
        m_m = m_mm * 1e-3
        b_m = psi_m * m_m
        res = calculate_gear(
            m_m=m_m,
            z1=z1,
            z2=z2,
            b_m=b_m,
            Mt1_Nm=Mt1_Nm,
            n1_rpm=n1_rpm,
            material_pinion=material_pinion,
            material_gear=material_gear,
            K_A=K_A,
        )
        status = "OK" if res.Cs >= target_cs else "insuffisant"
        evaluations.append(
            GearEvaluation(
                m_mm=m_mm,
                b_mm=b_m * 1e3,
                Cs=res.Cs,
                status=status,
                limiting_criterion=res.limiting_criterion,
            )
        )
        if status == "OK":
            return GearOptimizationResult(
                found=True,
                m_optimal_mm=m_mm,
                result=res,
                target_safety_factor=target_cs,
                psi_m=psi_m,
                evaluations=evaluations,
            )

    return GearOptimizationResult(
        found=False,
        m_optimal_mm=None,
        result=None,
        target_safety_factor=target_cs,
        psi_m=psi_m,
        evaluations=evaluations,
    )
