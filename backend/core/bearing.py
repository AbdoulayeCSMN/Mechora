"""Rolling-element bearing — dynamic (ISO 281) + static (ISO 76) check.

DYNAMIC (ISO 281)
    L10  = (C / P)^n            in millions of revolutions
    L10h = L10 × 10^6 / (60·N)  in hours
    n    = 3   for ball bearings, 10/3 for cylindrical rollers
    N    = rotation speed (rpm)

EQUIVALENT DYNAMIC LOAD P (ball-radial bearings, single row)
    P = X · Fr + Y · Fa
    (X, Y, e) interpolated linearly from the ISO X/Y table below using
    the ratio Fa/C0.
    If Fa / Fr ≤ e   →  X = 1,    Y = 0   →  P = Fr
    If Fa / Fr > e   →  X = 0.56, Y = (table)

    For cylindrical roller bearings (axial-incapable): P = Fr.

STATIC (ISO 76, ball bearings)
    P0 = max(Fr, 0.6·Fr + 0.5·Fa)
    S0 = C0 / P0
    Verdict:
        S0 < 0.5      → Insuffisant (risque déformation)
        0.5 ≤ S0 < 0.8 → Fonctionnement sans chocs limite
        0.8 ≤ S0 < 1.2 → Fonctionnement normal OK
        S0 ≥ 1.2      → Résistance aux chocs OK

REFERENCE LIVES (guide values)
    1 000 h      usage général
    5 000 h      véhicules
    20 000 h     machines 8 h/j
    50 000 h     service continu
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .advisor import Advice, generate_bearing_advice


# --------------------------------------------------------------------------- #
# Bearing types                                                                #
# --------------------------------------------------------------------------- #
class BearingType(str, Enum):
    # Ball bearings
    BALL_RADIAL = "ball_radial"                # alias historique de _1ROW
    BALL_RADIAL_1ROW = "ball_radial_1row"
    BALL_RADIAL_2ROW = "ball_radial_2row"
    BALL_OBLIQUE_1ROW = "ball_oblique_1row"    # nécessite alpha_deg
    # Roller bearings
    ROLLER_CYLINDRICAL = "roller_cylindrical"
    ROLLER_CONICAL = "roller_conical"          # peut prendre Fa, Y paramétrable


# Sets pour dispatch
BALL_RADIAL_TYPES: set[BearingType] = {
    BearingType.BALL_RADIAL,
    BearingType.BALL_RADIAL_1ROW,
    BearingType.BALL_RADIAL_2ROW,
}


BEARING_EXPONENT: dict[BearingType, float] = {
    BearingType.BALL_RADIAL:        3.0,
    BearingType.BALL_RADIAL_1ROW:   3.0,
    BearingType.BALL_RADIAL_2ROW:   3.0,
    BearingType.BALL_OBLIQUE_1ROW:  3.0,
    BearingType.ROLLER_CYLINDRICAL: 10.0 / 3.0,
    BearingType.ROLLER_CONICAL:     10.0 / 3.0,
}


# --------------------------------------------------------------------------- #
# ISO 281 X / Y / e interpolation table (single-row deep-groove ball bearing)  #
#                                                                              #
# Each row: (Fa/C0,  e,    X (if Fa/Fr > e),  Y (if Fa/Fr > e))                #
# --------------------------------------------------------------------------- #
XYE_TABLE_BALL_RADIAL: list[tuple[float, float, float, float]] = [
    (0.014, 0.19, 0.56, 2.30),
    (0.028, 0.22, 0.56, 1.99),
    (0.056, 0.26, 0.56, 1.71),
    (0.084, 0.28, 0.56, 1.55),
    (0.110, 0.30, 0.56, 1.45),
    (0.170, 0.34, 0.56, 1.31),
    (0.280, 0.38, 0.56, 1.15),
    (0.420, 0.42, 0.56, 1.04),
    (0.560, 0.44, 0.56, 1.00),
]


def interpolate_xye(fa_over_c0: float) -> Tuple[float, float, float]:
    """Linear interpolation of (e, X, Y) from the X/Y/e table.

    Clamps to the first/last row outside the tabulated range.
    """
    if fa_over_c0 <= XYE_TABLE_BALL_RADIAL[0][0]:
        _, e, X, Y = XYE_TABLE_BALL_RADIAL[0]
        return e, X, Y
    if fa_over_c0 >= XYE_TABLE_BALL_RADIAL[-1][0]:
        _, e, X, Y = XYE_TABLE_BALL_RADIAL[-1]
        return e, X, Y
    for i in range(len(XYE_TABLE_BALL_RADIAL) - 1):
        r1, e1, X1, Y1 = XYE_TABLE_BALL_RADIAL[i]
        r2, e2, X2, Y2 = XYE_TABLE_BALL_RADIAL[i + 1]
        if r1 <= fa_over_c0 <= r2:
            t = (fa_over_c0 - r1) / (r2 - r1)
            return (
                e1 + t * (e2 - e1),
                X1 + t * (X2 - X1),
                Y1 + t * (Y2 - Y1),
            )
    raise RuntimeError("X/Y/e interpolation failed (unexpected)")


# --------------------------------------------------------------------------- #
# Oblique single-row ball bearings : (e, X if Fa/Fr>e, Y if Fa/Fr>e) per α     #
#                                                                              #
# Below threshold e the convention is X = 1, Y = 0 (i.e. P = Fr).              #
# --------------------------------------------------------------------------- #
OBLIQUE_BALL_TABLE: dict[int, Tuple[float, float, float]] = {
    15: (1.14, 0.35, 0.57),
    20: (0.80, 0.39, 0.76),
    25: (0.95, 0.37, 0.66),
    30: (0.80, 0.35, 0.57),
}


def oblique_ball_xye(alpha_deg: float) -> Tuple[float, float, float]:
    """Lookup (e, X_gt_e, Y_gt_e) for an oblique single-row ball bearing.

    `alpha_deg` is the contact angle. The table is discrete (15/20/25/30°);
    we pick the nearest tabulated angle.
    """
    if alpha_deg <= 0:
        raise ValueError("alpha_deg must be > 0")
    key = min(OBLIQUE_BALL_TABLE, key=lambda a: abs(a - alpha_deg))
    return OBLIQUE_BALL_TABLE[key]


# --------------------------------------------------------------------------- #
# Equivalent load — dynamic (P) and static (P0)                                #
# --------------------------------------------------------------------------- #
def equivalent_load_dynamic(
    Fr_N: float,
    Fa_N: float,
    C0_N: float,
    bearing_type: BearingType,
    *,
    alpha_deg: Optional[float] = None,
    Y_conical: float = 1.5,
    e_conical: float = 0.4,
) -> Tuple[float, Optional[float], float, float]:
    """Return (P, e_used, X_used, Y_used).

    Per-type dispatch:
      - ROLLER_CYLINDRICAL : P = Fr (Fa ignored)
      - ROLLER_CONICAL     : X=1/Y=0 if Fa/Fr ≤ e_conical,
                             else X=0.40, Y=Y_conical (default 1.5)
      - BALL_OBLIQUE_1ROW  : table per α (15/20/25/30°)
      - BALL_RADIAL family : ISO 281 table interpolated on Fa/C0
                             (BALL_RADIAL, BALL_RADIAL_1ROW, BALL_RADIAL_2ROW)
    """
    # Cylindrical rollers: pure radial only
    if bearing_type is BearingType.ROLLER_CYLINDRICAL:
        return Fr_N, None, 1.0, 0.0

    # No axial: always P = Fr
    if Fa_N <= 0:
        return Fr_N, None, 1.0, 0.0

    fa_over_fr = (Fa_N / Fr_N) if Fr_N > 0 else float("inf")

    # Conical rollers
    if bearing_type is BearingType.ROLLER_CONICAL:
        if fa_over_fr <= e_conical:
            return Fr_N, e_conical, 1.0, 0.0
        P = 0.40 * Fr_N + Y_conical * Fa_N
        return P, e_conical, 0.40, Y_conical

    # Oblique balls (single row), depends on contact angle α
    if bearing_type is BearingType.BALL_OBLIQUE_1ROW:
        if alpha_deg is None:
            raise ValueError(
                "alpha_deg is required for BALL_OBLIQUE_1ROW "
                "(contact angle in degrees: 15/20/25/30)"
            )
        e, X_gt, Y_gt = oblique_ball_xye(alpha_deg)
        if fa_over_fr <= e:
            return Fr_N, e, 1.0, 0.0
        return X_gt * Fr_N + Y_gt * Fa_N, e, X_gt, Y_gt

    # Radial balls (1 or 2 rows) — ISO 281 X/Y/e interpolation
    if bearing_type in BALL_RADIAL_TYPES:
        if C0_N <= 0:
            raise ValueError(
                "C0_N (static rating) is required for ball-radial bearings when "
                "Fa_N > 0 — it drives X/Y/e via the ISO 281 table."
            )
        fa_over_c0 = Fa_N / C0_N
        e, X_tab, Y_tab = interpolate_xye(fa_over_c0)
        if fa_over_fr <= e:
            return Fr_N, e, 1.0, 0.0
        return X_tab * Fr_N + Y_tab * Fa_N, e, X_tab, Y_tab

    raise ValueError(f"unsupported bearing type: {bearing_type}")


def equivalent_load_static(
    Fr_N: float, Fa_N: float, bearing_type: BearingType
) -> float:
    """P0 per ISO 76. For cylindrical roller bearings: P0 = Fr."""
    if bearing_type is BearingType.ROLLER_CYLINDRICAL:
        return Fr_N
    return max(Fr_N, 0.6 * Fr_N + 0.5 * Fa_N)


# --------------------------------------------------------------------------- #
# Verdicts                                                                     #
# --------------------------------------------------------------------------- #
def dynamic_verdict(L10_hours: float, target_hours: float) -> str:
    if not math.isfinite(L10_hours):
        return "Insuffisant"
    if L10_hours < 0.5 * target_hours:
        return "Insuffisant"
    if L10_hours < target_hours:
        return "Limite"
    if L10_hours <= 3.0 * target_hours:
        return "OK"
    return "Surdimensionné"


def static_verdict(S0: float) -> str:
    if not math.isfinite(S0):
        return "Résistance aux chocs OK"
    if S0 < 0.5:
        return "Insuffisant (risque déformation)"
    if S0 < 0.8:
        return "Fonctionnement sans chocs limite"
    if S0 < 1.2:
        return "Fonctionnement normal OK"
    return "Résistance aux chocs OK"


# --------------------------------------------------------------------------- #
# Catalog (representative SKF-like values)                                     #
# --------------------------------------------------------------------------- #
class BearingCatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    designation: str
    type: BearingType
    C_N: float = Field(..., gt=0)
    C0_N: float = Field(..., gt=0)
    d_bore_mm: Optional[float] = None


DEFAULT_BALL_BEARING_CATALOG: list[BearingCatalogEntry] = [
    BearingCatalogEntry(designation="6200", type=BearingType.BALL_RADIAL, C_N=5_400,  C0_N=2_360,  d_bore_mm=10),
    BearingCatalogEntry(designation="6201", type=BearingType.BALL_RADIAL, C_N=6_900,  C0_N=3_100,  d_bore_mm=12),
    BearingCatalogEntry(designation="6202", type=BearingType.BALL_RADIAL, C_N=7_650,  C0_N=3_750,  d_bore_mm=15),
    BearingCatalogEntry(designation="6203", type=BearingType.BALL_RADIAL, C_N=9_950,  C0_N=4_750,  d_bore_mm=17),
    BearingCatalogEntry(designation="6204", type=BearingType.BALL_RADIAL, C_N=13_500, C0_N=6_550,  d_bore_mm=20),
    BearingCatalogEntry(designation="6205", type=BearingType.BALL_RADIAL, C_N=14_800, C0_N=7_800,  d_bore_mm=25),
    BearingCatalogEntry(designation="6206", type=BearingType.BALL_RADIAL, C_N=20_300, C0_N=11_200, d_bore_mm=30),
    BearingCatalogEntry(designation="6207", type=BearingType.BALL_RADIAL, C_N=25_500, C0_N=15_300, d_bore_mm=35),
    BearingCatalogEntry(designation="6208", type=BearingType.BALL_RADIAL, C_N=32_500, C0_N=19_000, d_bore_mm=40),
    BearingCatalogEntry(designation="6209", type=BearingType.BALL_RADIAL, C_N=35_100, C0_N=21_600, d_bore_mm=45),
    BearingCatalogEntry(designation="6210", type=BearingType.BALL_RADIAL, C_N=37_100, C0_N=23_200, d_bore_mm=50),
    BearingCatalogEntry(designation="6211", type=BearingType.BALL_RADIAL, C_N=46_200, C0_N=29_000, d_bore_mm=55),
    BearingCatalogEntry(designation="6212", type=BearingType.BALL_RADIAL, C_N=55_300, C0_N=36_000, d_bore_mm=60),
]


DEFAULT_ROLLER_BEARING_CATALOG: list[BearingCatalogEntry] = [
    BearingCatalogEntry(designation="NU 204", type=BearingType.ROLLER_CYLINDRICAL, C_N=25_500,  C0_N=24_000,  d_bore_mm=20),
    BearingCatalogEntry(designation="NU 205", type=BearingType.ROLLER_CYLINDRICAL, C_N=28_600,  C0_N=27_000,  d_bore_mm=25),
    BearingCatalogEntry(designation="NU 206", type=BearingType.ROLLER_CYLINDRICAL, C_N=44_000,  C0_N=43_000,  d_bore_mm=30),
    BearingCatalogEntry(designation="NU 207", type=BearingType.ROLLER_CYLINDRICAL, C_N=56_100,  C0_N=56_000,  d_bore_mm=35),
    BearingCatalogEntry(designation="NU 208", type=BearingType.ROLLER_CYLINDRICAL, C_N=71_500,  C0_N=73_500,  d_bore_mm=40),
    BearingCatalogEntry(designation="NU 209", type=BearingType.ROLLER_CYLINDRICAL, C_N=88_000,  C0_N=90_000,  d_bore_mm=45),
    BearingCatalogEntry(designation="NU 210", type=BearingType.ROLLER_CYLINDRICAL, C_N=89_000,  C0_N=100_000, d_bore_mm=50),
    BearingCatalogEntry(designation="NU 211", type=BearingType.ROLLER_CYLINDRICAL, C_N=121_000, C0_N=132_000, d_bore_mm=55),
    BearingCatalogEntry(designation="NU 212", type=BearingType.ROLLER_CYLINDRICAL, C_N=152_000, C0_N=170_000, d_bore_mm=60),
]


def get_bearing_catalog(bearing_type: BearingType) -> list[BearingCatalogEntry]:
    """Default sample catalog grouped by family (ball vs roller).

    For ball families (BALL_RADIAL/_1ROW/_2ROW/_OBLIQUE_1ROW) returns the
    series-6200 ball entries. For ROLLER_* returns the NU series.
    """
    if bearing_type in BALL_RADIAL_TYPES or bearing_type is BearingType.BALL_OBLIQUE_1ROW:
        return DEFAULT_BALL_BEARING_CATALOG
    return DEFAULT_ROLLER_BEARING_CATALOG


# --------------------------------------------------------------------------- #
# Result model                                                                 #
# --------------------------------------------------------------------------- #
class BearingResult(BaseModel):
    """Combined dynamic (ISO 281) + static (ISO 76) check result."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    C_N: float
    C0_N: float
    Fr_N: float
    Fa_N: float
    n_rpm: float
    bearing_type: BearingType
    target_hours: float

    # Dynamic
    P_N: float
    e_used: Optional[float]
    X_used: float
    Y_used: float
    L10_millions: float
    L10_hours: float
    verdict_dynamic: str

    # Static
    P0_N: float
    S0: float
    verdict_static: str

    advice: Advice


def calculate_bearing(
    C_N: float,
    C0_N: float,
    Fr_N: float,
    Fa_N: float,
    n_rpm: float,
    bearing_type: BearingType,
    target_hours: float = 20_000.0,
    *,
    alpha_deg: Optional[float] = None,
    Y_conical: float = 1.5,
    e_conical: float = 0.4,
) -> BearingResult:
    """Full ISO 281 + ISO 76 check.

    Extra arguments for special types:
      - alpha_deg : contact angle (deg) for BALL_OBLIQUE_1ROW (15/20/25/30)
      - Y_conical, e_conical : Y factor and e threshold for ROLLER_CONICAL
    """
    for name, val in (
        ("C_N", C_N), ("C0_N", C0_N), ("Fr_N", Fr_N),
        ("Fa_N", Fa_N), ("n_rpm", n_rpm),
    ):
        if not math.isfinite(val):
            raise ValueError(f"{name} must be a finite value")
    if C_N <= 0:
        raise ValueError("C_N (dynamic basic load rating) must be > 0")
    if C0_N < 0:
        raise ValueError("C0_N (static basic load rating) must be ≥ 0")
    if Fr_N < 0 or Fa_N < 0:
        raise ValueError("Loads Fr_N and Fa_N must be ≥ 0")
    if Fr_N == 0 and Fa_N == 0:
        raise ValueError("At least one of Fr_N or Fa_N must be > 0")
    if n_rpm <= 0:
        raise ValueError("n_rpm must be > 0")
    if target_hours <= 0:
        raise ValueError("target_hours must be > 0")
    if bearing_type in BALL_RADIAL_TYPES and Fa_N > 0 and C0_N == 0:
        raise ValueError(
            "C0_N must be > 0 for ball-radial bearings under axial load "
            "(used to interpolate X/Y/e)."
        )

    # Dynamic
    p_exp = BEARING_EXPONENT[bearing_type]
    P, e_used, X_used, Y_used = equivalent_load_dynamic(
        Fr_N, Fa_N, C0_N, bearing_type,
        alpha_deg=alpha_deg, Y_conical=Y_conical, e_conical=e_conical,
    )
    L10_million = (C_N / P) ** p_exp
    L10_hours = L10_million * 1e6 / (60.0 * n_rpm)
    vd = dynamic_verdict(L10_hours, target_hours)

    # Static
    P0 = equivalent_load_static(Fr_N, Fa_N, bearing_type)
    S0 = C0_N / P0 if C0_N > 0 and P0 > 0 else float("inf")
    vs = static_verdict(S0)

    advice = generate_bearing_advice(
        L10_hours=L10_hours,
        target_hours=target_hours,
        Fr_N=Fr_N,
        Fa_N=Fa_N,
        P_N=P,
        P0_N=P0,
        S0=S0,
        bearing_type=bearing_type,
        verdict_dynamic=vd,
        verdict_static=vs,
    )

    return BearingResult(
        C_N=C_N, C0_N=C0_N, Fr_N=Fr_N, Fa_N=Fa_N, n_rpm=n_rpm,
        bearing_type=bearing_type,
        target_hours=target_hours,
        P_N=P, e_used=e_used, X_used=X_used, Y_used=Y_used,
        L10_millions=L10_million, L10_hours=L10_hours,
        verdict_dynamic=vd,
        P0_N=P0, S0=S0, verdict_static=vs,
        advice=advice,
    )


# --------------------------------------------------------------------------- #
# Inverse formulas + catalog-aware optimization                                #
# --------------------------------------------------------------------------- #
def required_C(
    P_N: float, n_rpm: float, target_hours: float, bearing_type: BearingType
) -> float:
    """Minimum dynamic C required to reach target_hours at (P, n)."""
    p_exp = BEARING_EXPONENT[bearing_type]
    return P_N * (target_hours * 60.0 * n_rpm / 1e6) ** (1.0 / p_exp)


def required_C0(P0_N: float, S0_target: float = 1.0) -> float:
    """Minimum static C0 required to reach a target static safety factor."""
    return P0_N * S0_target


@dataclass(frozen=True)
class BearingEvaluation:
    entry: BearingCatalogEntry
    L10_hours: float
    S0: float
    status_dyn: Literal["OK", "Insuffisant"]
    status_stat: Literal["OK", "Insuffisant"]


@dataclass(frozen=True)
class BearingOptimizationResult:
    found: bool
    C_required_N: float
    C0_required_N: float
    P_N: float
    P0_N: float
    e_used: Optional[float]
    X_used: float
    Y_used: float
    S0_target: float
    optimal: Optional[BearingCatalogEntry]
    result: Optional[BearingResult]
    target_hours: float
    bearing_type: BearingType
    evaluations: List[BearingEvaluation]


def optimize_bearing(
    Fr_N: float,
    Fa_N: float,
    n_rpm: float,
    bearing_type: BearingType,
    target_hours: float,
    S0_target: float = 1.0,
    catalog: Optional[List[BearingCatalogEntry]] = None,
    *,
    alpha_deg: Optional[float] = None,
    Y_conical: float = 1.5,
    e_conical: float = 0.4,
) -> BearingOptimizationResult:
    """Closed-form required C and C0 + selection in the catalog.

    The catalog entry chosen is the smallest one whose C AND C0 both meet
    the required values. The evaluations list contains every candidate
    with its computed L10h and S0.
    """
    if Fr_N < 0 or Fa_N < 0:
        raise ValueError("Loads must be ≥ 0")
    if Fr_N == 0 and Fa_N == 0:
        raise ValueError("At least one of Fr_N or Fa_N must be > 0")
    if n_rpm <= 0:
        raise ValueError("n_rpm must be > 0")
    if target_hours <= 0:
        raise ValueError("target_hours must be > 0")
    if S0_target <= 0:
        raise ValueError("S0_target must be > 0")

    if catalog is None:
        catalog = get_bearing_catalog(bearing_type)
    # Allow BALL_RADIAL catalog entries to match all single-row ball types
    compatible = {bearing_type}
    if bearing_type in BALL_RADIAL_TYPES:
        compatible |= BALL_RADIAL_TYPES
    catalog_filtered = [b for b in catalog if b.type in compatible]
    catalog_sorted = sorted(catalog_filtered, key=lambda b: b.C_N)

    # P0 only depends on loads + type — straight forward
    P0 = equivalent_load_static(Fr_N, Fa_N, bearing_type)
    C0_req = required_C0(P0, S0_target)

    # P (dynamic) depends on C0 for ball-radial + Fa > 0. Use the required
    # C0 as a consistent estimate (one-shot, no iteration).
    C0_for_interp = max(C0_req, 1.0)
    P, e_used, X_used, Y_used = equivalent_load_dynamic(
        Fr_N, Fa_N, C0_for_interp, bearing_type,
        alpha_deg=alpha_deg, Y_conical=Y_conical, e_conical=e_conical,
    )
    C_req = required_C(P, n_rpm, target_hours, bearing_type)

    evaluations: list[BearingEvaluation] = []
    optimal: Optional[BearingCatalogEntry] = None
    optimal_result: Optional[BearingResult] = None
    for entry in catalog_sorted:
        try:
            r = calculate_bearing(
                C_N=entry.C_N, C0_N=entry.C0_N,
                Fr_N=Fr_N, Fa_N=Fa_N, n_rpm=n_rpm,
                bearing_type=bearing_type, target_hours=target_hours,
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
            BearingEvaluation(
                entry=entry,
                L10_hours=r.L10_hours,
                S0=r.S0,
                status_dyn=status_dyn,
                status_stat=status_stat,
            )
        )
        if optimal is None and status_dyn == "OK" and status_stat == "OK":
            optimal = entry
            optimal_result = r

    return BearingOptimizationResult(
        found=optimal is not None,
        C_required_N=C_req,
        C0_required_N=C0_req,
        P_N=P,
        P0_N=P0,
        e_used=e_used,
        X_used=X_used,
        Y_used=Y_used,
        S0_target=S0_target,
        optimal=optimal,
        result=optimal_result,
        target_hours=target_hours,
        bearing_type=bearing_type,
        evaluations=evaluations,
    )


# --------------------------------------------------------------------------- #
# Bearing set — équivalent LE10 d'un ensemble                                  #
#                                                                              #
#     LE10 = [Σ(1/Li10)^1.5]^(-1/1.5)                                          #
#                                                                              #
# Cours AP27 : pour 2 roulements de L10h=15000h et 25000h,                     #
# LE10 ≈ 11630 h (~ vérifié dans les tests).                                   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BearingSetResult:
    LE10_hours: float
    weakest_index: int             # index 0-based du roulement le plus faible
    weakest_L10_hours: float
    L10_hours_each: List[float]    # L10h de chaque roulement


def calculate_bearing_set(bearing_results: List[BearingResult]) -> BearingSetResult:
    """LE10 d'un ensemble de roulements + identification du goulot.

    Tous les roulements partagent la même rotation : on combine leurs
    durées de vie individuelles selon la formule de cumul (exposant 1.5).
    """
    if not bearing_results:
        raise ValueError("at least one bearing result is required")
    L10s: list[float] = []
    for i, r in enumerate(bearing_results):
        if r.L10_hours <= 0 or not math.isfinite(r.L10_hours):
            raise ValueError(f"L10_hours[{i}] must be > 0 and finite")
        L10s.append(r.L10_hours)

    s = sum((1.0 / L) ** 1.5 for L in L10s)
    LE10 = s ** (-1.0 / 1.5)
    weakest_idx = min(range(len(L10s)), key=lambda i: L10s[i])
    return BearingSetResult(
        LE10_hours=LE10,
        weakest_index=weakest_idx,
        weakest_L10_hours=L10s[weakest_idx],
        L10_hours_each=L10s,
    )


# --------------------------------------------------------------------------- #
# Variable loading — équivalent statistique Pe                                 #
#                                                                              #
#     Pe = (Σ ai · Pi^n)^(1/n)                                                 #
#     n = 3 pour billes, 10/3 pour rouleaux                                    #
#     Σ ai doit valoir 1                                                       #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VariableLoadPeriod:
    P_N: float                     # Charge équivalente pendant la période, N
    a_fraction: float              # Fraction de temps (Σ = 1)


@dataclass(frozen=True)
class VariableLoadResult:
    Pe_N: float                    # Charge équivalente cumulée
    n_exponent: float              # Exposant utilisé (3 ou 10/3)
    bearing_type: BearingType
    periods: List[VariableLoadPeriod]


def calculate_variable_load(
    periods: List[VariableLoadPeriod],
    bearing_type: BearingType,
) -> VariableLoadResult:
    """Charge équivalente Pe pour un profil de chargement variable."""
    if not periods:
        raise ValueError("at least one period is required")
    for i, p in enumerate(periods):
        if p.P_N <= 0 or not math.isfinite(p.P_N):
            raise ValueError(f"periods[{i}].P_N must be > 0 and finite")
        if p.a_fraction < 0 or p.a_fraction > 1:
            raise ValueError(
                f"periods[{i}].a_fraction must be in [0, 1], got {p.a_fraction}"
            )
    total = sum(p.a_fraction for p in periods)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Σ a_fraction must be 1.0, got {total:.6f} "
            f"({len(periods)} periods)"
        )

    n_exp = BEARING_EXPONENT[bearing_type]
    s = sum(p.a_fraction * (p.P_N ** n_exp) for p in periods)
    Pe = s ** (1.0 / n_exp)
    return VariableLoadResult(
        Pe_N=Pe,
        n_exponent=n_exp,
        bearing_type=bearing_type,
        periods=list(periods),
    )
