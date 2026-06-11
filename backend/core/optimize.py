"""Catalog-based beam optimization.

Walks a list of normalized profiles in ascending mass order and returns the
first one that satisfies both:
  * Cs >= target_safety_factor (strength)
  * f_max <= length / deflection_ratio (serviceability, default L/200)

Returns the full evaluation list as well so callers can render a comparison
table. Never raises when no profile fits — `optimal is None` is the answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from .beam import Beam, BeamResult, analyze
from .loads import DistributedLoad, PointLoad, SupportType
from .materials import Material
from .profiles import CatalogProfile
from .shaft import ShaftResult, ShaftSection, calculate_shaft


EvalStatus = Literal["OK", "Cs_insuffisant", "fleche_excessive"]


@dataclass(frozen=True)
class ProfileEvaluation:
    """Per-profile result inside an OptimizationResult."""

    profile: CatalogProfile
    status: EvalStatus
    Cs: float
    f_max_m: float           # SI; presentation layer converts to mm
    sigma_max_Pa: float
    M_max_Nm: float
    reason: Optional[str]    # human-readable explanation when not OK


@dataclass(frozen=True)
class OptimizationResult:
    optimal: Optional[CatalogProfile]
    optimal_result: Optional[BeamResult]
    evaluations: List[ProfileEvaluation]
    deflection_limit_m: float
    target_safety_factor: float


def optimize_beam_catalog(
    length: float,
    material: Material,
    support: SupportType,
    loads: List[PointLoad | DistributedLoad],
    target_safety_factor: float,
    catalog: List[CatalogProfile],
    deflection_ratio: float = 200.0,
) -> OptimizationResult:
    """Find the lightest profile in `catalog` meeting strength + serviceability.

    Parameters
    ----------
    length : float
        Beam length, m.
    material : Material
        Beam material (SI properties).
    support : SupportType
    loads : list of Load
    target_safety_factor : float
        Minimum acceptable Cs = Re / sigma_max.
    catalog : list of CatalogProfile
        Pool of candidate profiles (will be sorted internally by mass).
    deflection_ratio : float
        Maximum admissible deflection is `length / deflection_ratio`
        (default 200, i.e. L/200).

    Returns
    -------
    OptimizationResult
        `optimal` is None when no profile in `catalog` satisfies both criteria.
    """
    if target_safety_factor <= 0:
        raise ValueError("target_safety_factor must be > 0")
    if deflection_ratio <= 0:
        raise ValueError("deflection_ratio must be > 0")

    deflection_limit = length / deflection_ratio
    sorted_profiles = sorted(catalog, key=lambda p: p.mass_kg_per_m)

    evaluations: list[ProfileEvaluation] = []
    optimal: Optional[CatalogProfile] = None
    optimal_result: Optional[BeamResult] = None

    for prof in sorted_profiles:
        beam = Beam(
            length=length,
            material=material,
            section=prof,
            support=support,
            loads=loads,
        )
        res = analyze(beam)

        ok_cs = res.Cs >= target_safety_factor
        ok_def = res.f_max <= deflection_limit

        if ok_cs and ok_def:
            status: EvalStatus = "OK"
            reason = None
            if optimal is None:
                optimal, optimal_result = prof, res
        elif not ok_cs:
            status = "Cs_insuffisant"
            reason = (
                f"Cs = {res.Cs:.2f} < {target_safety_factor:.2f} "
                f"(σ_max = {res.sigma_max * 1e-6:.1f} MPa)"
            )
        else:
            status = "fleche_excessive"
            reason = (
                f"f_max = {res.f_max * 1e3:.2f} mm > "
                f"{deflection_limit * 1e3:.2f} mm (L/{deflection_ratio:g})"
            )

        evaluations.append(
            ProfileEvaluation(
                profile=prof,
                status=status,
                Cs=res.Cs,
                f_max_m=res.f_max,
                sigma_max_Pa=res.sigma_max,
                M_max_Nm=res.M_max,
                reason=reason,
            )
        )

    return OptimizationResult(
        optimal=optimal,
        optimal_result=optimal_result,
        evaluations=evaluations,
        deflection_limit_m=deflection_limit,
        target_safety_factor=target_safety_factor,
    )


# --------------------------------------------------------------------------- #
# Shaft optimization                                                           #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ShaftOptimizationResult:
    found: bool
    d_optimal_m: Optional[float]
    result: Optional[ShaftResult]
    target_safety_factor: float
    d_min_m: float
    d_max_m: float
    step_m: float
    candidates_evaluated: int


def optimize_shaft(
    material: Material,
    Mf_Nm: float,
    Mt_Nm: float,
    shaft_type: Literal["solid", "hollow"],
    target_cs: float,
    d_min_mm: float = 10.0,
    d_max_mm: float = 200.0,
    step_mm: float = 1.0,
    d_int_ratio: float = 0.7,
) -> ShaftOptimizationResult:
    """Find the smallest outer diameter (discrete sweep) satisfying Cs ≥ target_cs.

    Parameters
    ----------
    material : Material
    Mf_Nm, Mt_Nm : float
        Bending and torsion moments (N·m). At least one must be > 0.
    shaft_type : 'solid' | 'hollow'
    target_cs : float
        Minimum Cs requested.
    d_min_mm, d_max_mm : float
        Diameter search range (outer diameter for hollow).
    step_mm : float
        Diameter increment (mm).
    d_int_ratio : float
        For hollow shafts only: d_int = d_int_ratio * d_ext (0 < ratio < 1).

    Returns
    -------
    ShaftOptimizationResult
        `found` is False if no candidate in the range satisfies the criterion.
    """
    if target_cs <= 0:
        raise ValueError("target_cs must be > 0")
    if step_mm <= 0:
        raise ValueError("step_mm must be > 0")
    if d_min_mm <= 0 or d_max_mm <= 0:
        raise ValueError("diameters must be > 0")
    if d_min_mm > d_max_mm:
        raise ValueError("d_min_mm must be ≤ d_max_mm")
    if shaft_type == "hollow" and not (0 < d_int_ratio < 1):
        raise ValueError("d_int_ratio must be in (0, 1) for hollow shafts")

    candidates: list[float] = []
    d_mm = d_min_mm
    # Inclusive of d_max within step rounding tolerance
    while d_mm <= d_max_mm + 1e-9:
        candidates.append(d_mm)
        d_mm += step_mm

    for d_mm in candidates:
        d_ext = d_mm * 1e-3
        d_int = d_ext * d_int_ratio if shaft_type == "hollow" else 0.0
        section = ShaftSection(type=shaft_type, d_ext=d_ext, d_int=d_int)
        res = calculate_shaft(section, material, Mf_Nm, Mt_Nm)
        if res.Cs >= target_cs:
            return ShaftOptimizationResult(
                found=True,
                d_optimal_m=d_ext,
                result=res,
                target_safety_factor=target_cs,
                d_min_m=d_min_mm * 1e-3,
                d_max_m=d_max_mm * 1e-3,
                step_m=step_mm * 1e-3,
                candidates_evaluated=candidates.index(d_mm) + 1,
            )

    return ShaftOptimizationResult(
        found=False,
        d_optimal_m=None,
        result=None,
        target_safety_factor=target_cs,
        d_min_m=d_min_mm * 1e-3,
        d_max_m=d_max_mm * 1e-3,
        step_m=step_mm * 1e-3,
        candidates_evaluated=len(candidates),
    )
