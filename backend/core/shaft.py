"""Transmission-shaft analysis under combined bending + torsion.

A shaft sees a bending moment Mf (from radial forces — gears, belts, pulleys)
and a torsion moment Mt (transmitted torque). The Von Mises equivalent stress
combines them:

    σ_eq = √(σ_f² + 3·τ²)
    σ_f  = Mf / W_f      (bending stress)
    τ    = Mt / W_t      (torsion stress, average over the section)

For a circular cross-section:
    Solid:  W_f = π·d³/32,            W_t = π·d³/16
    Hollow: W_f = π(D⁴ − d⁴)/(32·D),  W_t = π(D⁴ − d⁴)/(16·D)
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .advisor import Advice, generate_shaft_advice
from .beam import VerdictThresholds, verdict
from .materials import Material


class ShaftSection(BaseModel):
    """Cross-section of a circular shaft (solid or hollow).

    Stored in SI (m). Geometric properties (`W_f`, `W_t`, `area`) are
    exposed as derived properties.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["solid", "hollow"] = Field(..., description="Solid or hollow shaft")
    d_ext: float = Field(..., gt=0, description="Outer diameter, m")
    d_int: float = Field(0.0, ge=0, description="Inner diameter, m (0 for solid)")

    @field_validator("d_ext", "d_int")
    @classmethod
    def _finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("diameter must be finite")
        return v

    @model_validator(mode="after")
    def _check_dims(self) -> "ShaftSection":
        if self.type == "solid":
            if self.d_int != 0.0:
                raise ValueError("solid shaft must have d_int = 0")
        else:  # hollow
            if self.d_int <= 0:
                raise ValueError("hollow shaft must have d_int > 0")
            if self.d_int >= self.d_ext:
                raise ValueError("d_int must be < d_ext")
        return self

    @property
    def area(self) -> float:           # m²
        return math.pi * (self.d_ext ** 2 - self.d_int ** 2) / 4.0

    @property
    def W_f(self) -> float:            # m³, bending section modulus
        if self.type == "solid":
            return math.pi * self.d_ext ** 3 / 32.0
        return (
            math.pi
            * (self.d_ext ** 4 - self.d_int ** 4)
            / (32.0 * self.d_ext)
        )

    @property
    def W_t(self) -> float:            # m³, polar (torsion) section modulus
        if self.type == "solid":
            return math.pi * self.d_ext ** 3 / 16.0
        return (
            math.pi
            * (self.d_ext ** 4 - self.d_int ** 4)
            / (16.0 * self.d_ext)
        )


class ShaftResult(BaseModel):
    """Analysis output for a shaft under combined bending + torsion."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    section: ShaftSection
    sigma_f_Pa: float
    tau_Pa: float
    sigma_eq_Pa: float
    Cs: float
    verdict: str
    advice: Advice


def calculate_shaft(
    section: ShaftSection,
    material: Material,
    Mf_Nm: float,
    Mt_Nm: float,
    thresholds: VerdictThresholds = VerdictThresholds(),
) -> ShaftResult:
    """Compute σ_f, τ, σ_eq, Cs, verdict and advice for a shaft.

    Mf_Nm and Mt_Nm are magnitudes (≥ 0). At least one must be > 0.
    """
    if not math.isfinite(Mf_Nm) or Mf_Nm < 0:
        raise ValueError("Mf_Nm must be a finite value ≥ 0")
    if not math.isfinite(Mt_Nm) or Mt_Nm < 0:
        raise ValueError("Mt_Nm must be a finite value ≥ 0")
    if Mf_Nm == 0 and Mt_Nm == 0:
        raise ValueError("At least one of Mf_Nm or Mt_Nm must be > 0")

    sigma_f = Mf_Nm / section.W_f
    tau = Mt_Nm / section.W_t
    sigma_eq = math.sqrt(sigma_f ** 2 + 3.0 * tau ** 2)

    cs = float("inf") if sigma_eq == 0.0 else material.Re_effective / sigma_eq
    v = verdict(cs, thresholds)
    advice = generate_shaft_advice(
        material=material,
        sigma_f_Pa=sigma_f,
        tau_Pa=tau,
        sigma_eq_Pa=sigma_eq,
        cs=cs,
        verdict_str=v,
    )

    return ShaftResult(
        section=section,
        sigma_f_Pa=sigma_f,
        tau_Pa=tau,
        sigma_eq_Pa=sigma_eq,
        Cs=cs,
        verdict=v,
        advice=advice,
    )
