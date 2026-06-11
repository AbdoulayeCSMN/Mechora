"""Detailed real bearing catalogue — single-row deep-groove ball bearings
(SKF-equivalent values from the AP27 course handout, series 6000).

Each entry carries C (dynamic), C0 (static), bore d, outer D and width B.
Indexed by bore diameter so the optimiser can filter on the shaft diameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from .bearing import (
    BEARING_EXPONENT,
    BALL_RADIAL_TYPES,
    BearingType,
    BearingResult,
    calculate_bearing,
    equivalent_load_dynamic,
)


@dataclass(frozen=True)
class RealBearingEntry:
    designation: str          # ex. "6204"
    type: BearingType         # BALL_RADIAL_1ROW (mappable à BALL_RADIAL)
    d_bore_mm: float
    D_outer_mm: float
    B_width_mm: float
    C_N: float
    C0_N: float


def _b(des, d, D, B, C, C0) -> RealBearingEntry:
    return RealBearingEntry(
        designation=des, type=BearingType.BALL_RADIAL,
        d_bore_mm=d, D_outer_mm=D, B_width_mm=B,
        C_N=C, C0_N=C0,
    )


# --------------------------------------------------------------------------- #
# Catalogue série 6000 (handout cours AP27)                                    #
# --------------------------------------------------------------------------- #
REAL_BEARING_CATALOG: list[RealBearingEntry] = [
    # d = 17 mm
    _b("6203",  17,  40, 12,  9_600,  4_800),
    _b("6303",  17,  47, 14,  13_600, 6_600),
    _b("6403",  17,  62, 17,  22_700, 10_800),

    # d = 20 mm
    _b("61804", 20,  32,  7,  2_950,  1_870),
    _b("61904", 20,  37,  9,  6_400,  3_700),
    _b("16004", 20,  42,  8,  6_800,  4_100),
    _b("6004",  20,  42, 12,  9_400,  5_000),
    _b("6204",  20,  47, 14,  12_800, 6_700),
    _b("6304",  20,  52, 15,  15_900, 7_900),
    _b("6404",  20,  72, 19,  29_500, 15_500),

    # d = 25 mm
    _b("61805", 25,  37,  7,  4_300,  2_950),
    _b("61905", 25,  42,  9,  7_000,  4_550),
    _b("16005", 25,  47,  8,  10_100, 5_900),
    _b("6005",  25,  47, 12,  10_100, 5_900),
    _b("6205",  25,  52, 15,  14_000, 7_900),
    _b("6305",  25,  62, 17,  22_400, 11_500),
    _b("6405",  25,  80, 21,  36_000, 19_300),

    # d = 30 mm
    _b("61806", 30,  42,  7,  4_550,  3_400),
    _b("61906", 30,  47,  9,  7_200,  4_350),
    _b("16006", 30,  55,  9,  11_200, 7_400),
    _b("6006",  30,  55, 13,  13_200, 8_300),
    _b("6206",  30,  62, 16,  19_500, 11_300),
    _b("6306",  30,  72, 19,  28_000, 15_800),
    _b("6406",  30,  90, 23,  43_500, 23_800),

    # d = 35 mm
    _b("6007",  35,  62, 14,  16_000, 10_300),
    _b("6207",  35,  72, 17,  25_500, 15_300),
    _b("6307",  35,  80, 21,  33_500, 19_200),
    _b("6407",  35, 100, 25,  55_000, 31_000),

    # d = 40 mm
    _b("6008",  40,  68, 15,  16_000, 11_500),
    _b("6208",  40,  80, 18,  29_000, 17_900),
    _b("6308",  40,  90, 23,  40_500, 23_900),
    _b("6408",  40, 110, 27,  63_000, 36_500),
]


def list_bore_diameters() -> list[float]:
    """Return the unique bore diameters available in the catalog (sorted)."""
    return sorted({e.d_bore_mm for e in REAL_BEARING_CATALOG})


def get_real_catalog(d_arbre_mm: Optional[float] = None) -> list[RealBearingEntry]:
    """Return catalog entries, optionally filtered by exact bore diameter."""
    if d_arbre_mm is None:
        return list(REAL_BEARING_CATALOG)
    return [e for e in REAL_BEARING_CATALOG
            if abs(e.d_bore_mm - d_arbre_mm) < 0.5]


# --------------------------------------------------------------------------- #
# Optimisation depuis le catalogue réel                                        #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RealCatalogEvaluation:
    entry: RealBearingEntry
    L10_hours: float
    S0: float
    status_dyn: Literal["OK", "Insuffisant"]
    status_stat: Literal["OK", "Insuffisant"]


@dataclass(frozen=True)
class RealCatalogOptimizationResult:
    found: bool
    C_required_N: float        # C minimale estimée via C0_estimate (premier passage)
    optimal: Optional[RealBearingEntry]
    result: Optional[BearingResult]
    target_hours: float
    bearing_type: BearingType
    d_arbre_mm: Optional[float]
    evaluations: List[RealCatalogEvaluation]


def optimize_bearing_catalog(
    Fr_N: float,
    Fa_N: float,
    C0_estimate_N: float,
    n_rpm: float,
    bearing_type: BearingType,
    target_hours: float,
    d_arbre_mm: Optional[float] = None,
    S0_target: float = 1.0,
    *,
    alpha_deg: Optional[float] = None,
    Y_conical: float = 1.5,
    e_conical: float = 0.4,
) -> RealCatalogOptimizationResult:
    """Trouve la référence du catalogue réel la plus économique.

    Pour chaque candidat compatible avec `bearing_type` (et le filtre
    `d_arbre_mm` si précisé) on calcule L10h avec son propre C0, et on
    retient le premier (plus petit C) qui satisfait L10h ≥ target_hours
    ET S0 ≥ S0_target.
    """
    if Fr_N < 0 or Fa_N < 0:
        raise ValueError("Loads must be ≥ 0")
    if Fr_N == 0 and Fa_N == 0:
        raise ValueError("At least one of Fr_N or Fa_N must be > 0")
    if n_rpm <= 0:
        raise ValueError("n_rpm must be > 0")
    if target_hours <= 0:
        raise ValueError("target_hours must be > 0")
    if C0_estimate_N <= 0:
        raise ValueError("C0_estimate_N must be > 0")
    if S0_target <= 0:
        raise ValueError("S0_target must be > 0")

    # Premier estimé de C requise via P(C0_estimate)
    P_est, _, _, _ = equivalent_load_dynamic(
        Fr_N, Fa_N, C0_estimate_N, bearing_type,
        alpha_deg=alpha_deg, Y_conical=Y_conical, e_conical=e_conical,
    )
    n_exp = BEARING_EXPONENT[bearing_type]
    C_req = P_est * (target_hours * 60.0 * n_rpm / 1e6) ** (1.0 / n_exp)

    # Filtre type compatible + diamètre
    compatible = {bearing_type}
    if bearing_type in BALL_RADIAL_TYPES:
        compatible |= BALL_RADIAL_TYPES
    pool = [e for e in REAL_BEARING_CATALOG if e.type in compatible]
    if d_arbre_mm is not None:
        pool = [e for e in pool if abs(e.d_bore_mm - d_arbre_mm) < 0.5]
    pool.sort(key=lambda e: e.C_N)

    evaluations: list[RealCatalogEvaluation] = []
    optimal: Optional[RealBearingEntry] = None
    optimal_result: Optional[BearingResult] = None

    for entry in pool:
        try:
            r = calculate_bearing(
                C_N=entry.C_N, C0_N=entry.C0_N,
                Fr_N=Fr_N, Fa_N=Fa_N, n_rpm=n_rpm,
                bearing_type=bearing_type,
                target_hours=target_hours,
                alpha_deg=alpha_deg, Y_conical=Y_conical, e_conical=e_conical,
            )
        except ValueError:
            continue
        status_dyn: Literal["OK", "Insuffisant"] = (
            "OK" if r.L10_hours >= target_hours else "Insuffisant"
        )
        status_stat: Literal["OK", "Insuffisant"] = (
            "OK" if r.S0 >= S0_target else "Insuffisant"
        )
        evaluations.append(
            RealCatalogEvaluation(
                entry=entry, L10_hours=r.L10_hours, S0=r.S0,
                status_dyn=status_dyn, status_stat=status_stat,
            )
        )
        if optimal is None and status_dyn == "OK" and status_stat == "OK":
            optimal = entry
            optimal_result = r

    return RealCatalogOptimizationResult(
        found=optimal is not None,
        C_required_N=C_req,
        optimal=optimal,
        result=optimal_result,
        target_hours=target_hours,
        bearing_type=bearing_type,
        d_arbre_mm=d_arbre_mm,
        evaluations=evaluations,
    )
