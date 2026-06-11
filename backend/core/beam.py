"""Beam bending analysis engine — pure RDM, SI units, no I/O.

Sign conventions:
- x increases from left end to right end.
- Downward loads are positive (magnitude > 0).
- Bending moment M(x) is positive when sagging (fibers below neutral axis in tension).
- Deflection f(x) returned as a downward magnitude (>= 0 at point of interest).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .loads import DistributedLoad, Load, PointLoad, SupportType
from .materials import Material
from .sections import Section

_EPS = 1e-12


# --------------------------------------------------------------------------- #
# Verdict thresholds                                                           #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VerdictThresholds:
    """Safety-factor thresholds used to label a design."""

    under: float = 1.0     # Cs < under                    -> "Sous-dimensionné"
    limit: float = 1.5     # under <= Cs < limit           -> "Limite"
    over: float = 4.0      # limit <= Cs <= over           -> "OK", else "Surdimensionné"


def verdict(cs: float, t: VerdictThresholds = VerdictThresholds()) -> str:
    if cs < t.under:
        return "Sous-dimensionné"
    if cs < t.limit:
        return "Limite"
    if cs <= t.over:
        return "OK"
    return "Surdimensionné"


# --------------------------------------------------------------------------- #
# Beam model                                                                   #
# --------------------------------------------------------------------------- #
class Beam(BaseModel):
    """Beam to analyze."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    length: float = Field(..., description="Span L, m (> 0)")
    material: Material
    section: Section
    support: SupportType
    loads: List[Load] = Field(default_factory=list)

    @field_validator("length")
    @classmethod
    def _positive_length(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("beam length must be > 0 m")
        return v

    @model_validator(mode="after")
    def _check_load_positions(self) -> "Beam":
        L = self.length
        for ld in self.loads:
            if isinstance(ld, PointLoad):
                if ld.position > L + _EPS:
                    raise ValueError(
                        f"point load position {ld.position} m exceeds beam length {L} m"
                    )
            elif isinstance(ld, DistributedLoad):
                if ld.end > L + _EPS:
                    raise ValueError(
                        f"distributed load end {ld.end} m exceeds beam length {L} m"
                    )
        return self


class BeamResult(BaseModel):
    """Analysis output."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    reactions: dict[str, float]
    x: list[float]
    V: list[float]
    M: list[float]
    M_max: float
    sigma_max: float
    f_max: float
    Cs: float
    verdict: str


# --------------------------------------------------------------------------- #
# Reactions                                                                    #
# --------------------------------------------------------------------------- #
def _load_resultants(ld: Load) -> tuple[float, float]:
    """Return (total force in N, centroid position in m) for a load."""
    if isinstance(ld, PointLoad):
        return ld.magnitude, ld.position
    # DistributedLoad
    length = ld.end - ld.start
    return ld.magnitude * length, 0.5 * (ld.start + ld.end)


def _reactions(beam: Beam) -> dict[str, float]:
    L = beam.length
    if beam.support is SupportType.SIMPLY_SUPPORTED:
        Ra = 0.0
        Rb = 0.0
        for ld in beam.loads:
            F, xc = _load_resultants(ld)
            Ra += F * (L - xc) / L
            Rb += F * xc / L
        return {"Ra": Ra, "Rb": Rb}

    # CANTILEVER fixed at x=0
    R = 0.0
    M_r = 0.0  # moment reaction magnitude at the wall (CW = balances load)
    for ld in beam.loads:
        F, xc = _load_resultants(ld)
        R += F
        M_r += F * xc
    return {"R": R, "M_r": M_r}


# --------------------------------------------------------------------------- #
# Shear and bending moment along the beam                                      #
# --------------------------------------------------------------------------- #
def _shear_moment(beam: Beam, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute V(x) and M(x) at each sample point by superposition."""
    L = beam.length
    V = np.zeros_like(x)
    M = np.zeros_like(x)

    if beam.support is SupportType.SIMPLY_SUPPORTED:
        for ld in beam.loads:
            if isinstance(ld, PointLoad):
                a = ld.position
                b = L - a
                P = ld.magnitude
                Ra = P * b / L
                left = x < a - _EPS
                # Use left-side FBD: V = Ra - sum(loads left of x)
                V += np.where(left, Ra, Ra - P)
                M += np.where(left, Ra * x, Ra * x - P * (x - a))
            else:  # DistributedLoad
                x1, x2 = ld.start, ld.end
                q = ld.magnitude
                F_tot = q * (x2 - x1)
                xc = 0.5 * (x1 + x2)
                Ra = F_tot * (L - xc) / L
                # Distributed contribution at x:
                # before x1 -> 0; inside -> q*(x - x1); after -> F_tot
                inside = (x >= x1) & (x <= x2)
                after = x > x2
                load_on_left = np.zeros_like(x)
                load_on_left = np.where(inside, q * (x - x1), load_on_left)
                load_on_left = np.where(after, F_tot, load_on_left)
                # moment of the distributed load that is left of x, about x
                # inside: q*(x - x1)^2 / 2
                # after : F_tot * (x - xc)
                m_left = np.zeros_like(x)
                m_left = np.where(inside, q * (x - x1) ** 2 / 2.0, m_left)
                m_left = np.where(after, F_tot * (x - xc), m_left)
                V += Ra - load_on_left
                M += Ra * x - m_left
        return V, M

    # CANTILEVER fixed at x=0
    # Use right-side FBD: V(x) = sum loads to the right of x; M(x) = -sum(load * (pos - x))
    # Convention: hogging M is negative.
    for ld in beam.loads:
        if isinstance(ld, PointLoad):
            a = ld.position
            P = ld.magnitude
            right = x < a + _EPS
            V += np.where(right, -P, 0.0)        # shear has opposite sign to load with this convention
            M += np.where(right, -P * (a - x), 0.0)
        else:
            x1, x2 = ld.start, ld.end
            q = ld.magnitude
            # contribution of portion of distributed load to the right of x at section x
            # if x <= x1: full load on right -> V = -q*(x2-x1); M = -q*(x2-x1)*((x1+x2)/2 - x)
            # if x1 < x < x2: partial -> V = -q*(x2-x), M = -q*(x2-x)^2/2
            # if x >= x2: 0
            left_of = x <= x1 + _EPS
            inside = (x > x1 + _EPS) & (x < x2 - _EPS)
            F_full = q * (x2 - x1)
            xc = 0.5 * (x1 + x2)
            V += np.where(left_of, -F_full, np.where(inside, -q * (x2 - x), 0.0))
            M += np.where(
                left_of,
                -F_full * (xc - x),
                np.where(inside, -q * (x2 - x) ** 2 / 2.0, 0.0),
            )
    # By construction, with our sign choice V > 0 on the right means downward to the right.
    # Flip to recover "positive shear = right side goes down relative to left side"
    V = -V
    return V, M


# --------------------------------------------------------------------------- #
# Deflection                                                                   #
# --------------------------------------------------------------------------- #
def _analytical_f_max(beam: Beam) -> float | None:
    """Return f_max (m, positive downward) for canonical single-load cases, else None."""
    if len(beam.loads) != 1:
        return None
    L = beam.length
    EI = beam.material.E * beam.section.inertia
    ld = beam.loads[0]

    if beam.support is SupportType.SIMPLY_SUPPORTED:
        if isinstance(ld, PointLoad) and abs(ld.position - L / 2) < 1e-9 * L:
            return ld.magnitude * L ** 3 / (48.0 * EI)
        if isinstance(ld, DistributedLoad) and ld.start <= _EPS and abs(ld.end - L) < 1e-9 * L:
            return 5.0 * ld.magnitude * L ** 4 / (384.0 * EI)

    if beam.support is SupportType.CANTILEVER:
        if isinstance(ld, PointLoad) and abs(ld.position - L) < 1e-9 * L:
            return ld.magnitude * L ** 3 / (3.0 * EI)
        if isinstance(ld, DistributedLoad) and ld.start <= _EPS and abs(ld.end - L) < 1e-9 * L:
            return ld.magnitude * L ** 4 / (8.0 * EI)

    return None


def _numerical_f_max(beam: Beam, x: np.ndarray, M: np.ndarray) -> float:
    """Double-integrate M/(EI) with BCs to get max downward deflection magnitude."""
    EI = beam.material.E * beam.section.inertia
    # f''(x) = -M / EI  with f positive downward, M sagging positive.
    rhs = -M / EI

    # Cumulative trapezoidal integration
    slope = np.zeros_like(x)
    slope[1:] = np.cumsum(0.5 * (rhs[1:] + rhs[:-1]) * np.diff(x))

    defl = np.zeros_like(x)
    defl[1:] = np.cumsum(0.5 * (slope[1:] + slope[:-1]) * np.diff(x))

    if beam.support is SupportType.SIMPLY_SUPPORTED:
        # BCs: f(0)=0 (already), f(L)=0 -> add linear slope correction
        c = -defl[-1] / (x[-1] - x[0])
        defl = defl + c * (x - x[0])
    # Cantilever: f(0)=0 and f'(0)=0 are already satisfied by zero ICs.

    return float(np.max(np.abs(defl)))


# --------------------------------------------------------------------------- #
# Public entry point                                                           #
# --------------------------------------------------------------------------- #
def analyze(
    beam: Beam,
    n_samples: int = 401,
    thresholds: VerdictThresholds = VerdictThresholds(),
) -> BeamResult:
    """Run a complete bending analysis of `beam`.

    All quantities returned in SI: N, N*m, Pa, m.
    """
    L = beam.length

    # Sample x: uniform grid + load discontinuities, sorted unique.
    base = np.linspace(0.0, L, n_samples)
    extras = [0.0, L]
    for ld in beam.loads:
        if isinstance(ld, PointLoad):
            extras.append(ld.position)
        else:
            extras.extend([ld.start, ld.end])
    x = np.unique(np.concatenate([base, np.array(extras, dtype=float)]))

    V, M = _shear_moment(beam, x)

    M_max = float(np.max(np.abs(M)))
    W = beam.section.section_modulus
    sigma_max = M_max / W

    f_max = _analytical_f_max(beam)
    if f_max is None:
        f_max = _numerical_f_max(beam, x, M)

    # Safety factor (avoid division-by-zero when there is no load)
    if sigma_max == 0.0:
        cs = float("inf")
    else:
        cs = beam.material.Re_effective / sigma_max

    return BeamResult(
        reactions=_reactions(beam),
        x=x.tolist(),
        V=V.tolist(),
        M=M.tolist(),
        M_max=M_max,
        sigma_max=sigma_max,
        f_max=f_max,
        Cs=cs,
        verdict=verdict(cs, thresholds),
    )
