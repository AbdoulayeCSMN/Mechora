"""Tests for the bearing module (ISO 281 dynamic + ISO 76 static)."""

import math

import pytest

from core.bearing import (
    BearingType,
    DEFAULT_BALL_BEARING_CATALOG,
    XYE_TABLE_BALL_RADIAL,
    calculate_bearing,
    dynamic_verdict,
    equivalent_load_dynamic,
    equivalent_load_static,
    interpolate_xye,
    optimize_bearing,
    required_C,
    static_verdict,
)


# --------------------------------------------------------------------------- #
# Course exercise 1 (AP27): ball radial bearing with combined load             #
#                                                                              #
# Given:  C = 12 800 N,  C0 = 6 600 N,  Fr = 4 000 N,  Fa = 2 500 N,           #
#         n = 200 rpm,  ball radial                                            #
#                                                                              #
# Hand checks:                                                                 #
#   Fa/C0 = 2500/6600 = 0.3788                                                 #
#     → interpolate in the table between (0.280, 0.38, 0.56, 1.15)             #
#                              and (0.420, 0.42, 0.56, 1.04)                   #
#     → e ≈ 0.3883, Y ≈ 1.1213                                                 #
#   Fa/Fr = 2500/4000 = 0.625 > e → P = 0.56·Fr + Y·Fa                         #
#   L10 = (C/P)^3 in millions of revolutions                                   #
#   L10h = L10 × 10^6 / (60·n)                                                 #
# --------------------------------------------------------------------------- #
def test_course_exercise_1_ball_with_combined_load():
    res = calculate_bearing(
        C_N=12_800, C0_N=6_600,
        Fr_N=4_000, Fa_N=2_500,
        n_rpm=200,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=20_000,
    )

    # Verify the X/Y/e interpolation
    e_used, X_used, Y_used = interpolate_xye(2500 / 6600)
    assert res.e_used == pytest.approx(e_used, rel=1e-9)
    assert res.X_used == pytest.approx(0.56, rel=1e-9)
    assert res.Y_used == pytest.approx(Y_used, rel=1e-9)

    expected_P = 0.56 * 4_000 + Y_used * 2_500
    assert res.P_N == pytest.approx(expected_P, rel=1e-9)

    # L10 (millions) and L10h
    expected_L10 = (12_800 / expected_P) ** 3
    expected_L10h = expected_L10 * 1e6 / (60 * 200)
    assert res.L10_millions == pytest.approx(expected_L10, rel=1e-9)
    assert res.L10_hours == pytest.approx(expected_L10h, rel=1e-9)


# --------------------------------------------------------------------------- #
# Course exercise 2: cylindrical roller bearing, no axial load                 #
# C = 28 000 N, Fr = 6 000 N, Fa = 0, n = 200 rpm                              #
# --------------------------------------------------------------------------- #
def test_course_exercise_2_roller_no_axial():
    res = calculate_bearing(
        C_N=28_000, C0_N=29_000,        # C0 ≈ C for rollers (representative)
        Fr_N=6_000, Fa_N=0,
        n_rpm=200,
        bearing_type=BearingType.ROLLER_CYLINDRICAL,
        target_hours=20_000,
    )
    assert res.P_N == pytest.approx(6_000)
    expected_L10 = (28_000 / 6_000) ** (10 / 3)
    expected_L10h = expected_L10 * 1e6 / (60 * 200)
    assert res.L10_millions == pytest.approx(expected_L10, rel=1e-9)
    assert res.L10_hours == pytest.approx(expected_L10h, rel=1e-9)


def test_fa_zero_ball_yields_P_equals_Fr():
    res = calculate_bearing(
        C_N=20_000, C0_N=10_000,
        Fr_N=4_000, Fa_N=0,
        n_rpm=1_500,
        bearing_type=BearingType.BALL_RADIAL,
    )
    assert res.P_N == pytest.approx(4_000)
    assert res.e_used is None  # table not applicable when Fa = 0


# --------------------------------------------------------------------------- #
# X/Y/e interpolation table                                                    #
# --------------------------------------------------------------------------- #
def test_xye_interpolation_at_tabulated_points():
    for ratio, e_exp, X_exp, Y_exp in XYE_TABLE_BALL_RADIAL:
        e, X, Y = interpolate_xye(ratio)
        assert e == pytest.approx(e_exp, rel=1e-9)
        assert X == pytest.approx(X_exp, rel=1e-9)
        assert Y == pytest.approx(Y_exp, rel=1e-9)


def test_xye_interpolation_between_points():
    # Midpoint between rows 7 (0.280) and 8 (0.420): Fa/C0 = 0.35
    e, X, Y = interpolate_xye(0.35)
    # Linear interp: e = (0.38 + 0.42)/2 = 0.40, Y = (1.15 + 1.04)/2 = 1.095
    assert e == pytest.approx(0.40, rel=1e-6)
    assert X == pytest.approx(0.56, rel=1e-9)
    assert Y == pytest.approx(1.095, rel=1e-6)


def test_xye_clamping_outside_range():
    # Below smallest tabulated → row 1
    e, X, Y = interpolate_xye(0.001)
    assert (e, Y) == (0.19, 2.30)
    # Above largest tabulated → last row
    e, X, Y = interpolate_xye(0.9)
    assert (e, Y) == (0.44, 1.00)


# --------------------------------------------------------------------------- #
# Equivalent loads                                                             #
# --------------------------------------------------------------------------- #
def test_dynamic_P_branches_on_fa_fr_vs_e():
    # Choose Fa/C0 = 0.1 → e ≈ 0.297 (interpolated). Fa = 1000, Fr_high so
    # Fa/Fr < e → P = Fr branch.
    P_low, e_lo, X_lo, Y_lo = equivalent_load_dynamic(
        Fr_N=10_000, Fa_N=1_000, C0_N=10_000,
        bearing_type=BearingType.BALL_RADIAL,
    )
    assert P_low == pytest.approx(10_000)
    assert X_lo == 1.0 and Y_lo == 0.0

    # Same C0/Fa but small Fr so Fa/Fr > e → use table values
    P_hi, e_hi, X_hi, Y_hi = equivalent_load_dynamic(
        Fr_N=2_000, Fa_N=1_000, C0_N=10_000,
        bearing_type=BearingType.BALL_RADIAL,
    )
    assert X_hi == pytest.approx(0.56)
    assert P_hi == pytest.approx(0.56 * 2_000 + Y_hi * 1_000, rel=1e-9)


def test_static_P0_formula_ball():
    P0 = equivalent_load_static(Fr_N=4_000, Fa_N=2_500, bearing_type=BearingType.BALL_RADIAL)
    expected = max(4_000, 0.6 * 4_000 + 0.5 * 2_500)
    assert P0 == pytest.approx(expected)


def test_static_P0_for_roller_is_Fr():
    P0 = equivalent_load_static(Fr_N=6_000, Fa_N=1_000, bearing_type=BearingType.ROLLER_CYLINDRICAL)
    assert P0 == pytest.approx(6_000)


# --------------------------------------------------------------------------- #
# Verdicts                                                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "L10h, target, expected",
    [
        (5_000,  20_000, "Insuffisant"),
        (15_000, 20_000, "Limite"),
        (25_000, 20_000, "OK"),
        (60_000, 20_000, "OK"),
        (61_000, 20_000, "Surdimensionné"),
    ],
)
def test_dynamic_verdict_thresholds(L10h, target, expected):
    assert dynamic_verdict(L10h, target) == expected


@pytest.mark.parametrize(
    "S0, expected",
    [
        (0.4, "Insuffisant (risque déformation)"),
        (0.6, "Fonctionnement sans chocs limite"),
        (1.0, "Fonctionnement normal OK"),
        (1.5, "Résistance aux chocs OK"),
    ],
)
def test_static_verdict_thresholds(S0, expected):
    assert static_verdict(S0) == expected


def test_S0_calculated_correctly():
    res = calculate_bearing(
        C_N=12_800, C0_N=6_600,
        Fr_N=4_000, Fa_N=2_500,
        n_rpm=200,
        bearing_type=BearingType.BALL_RADIAL,
    )
    expected_P0 = max(4_000, 0.6 * 4_000 + 0.5 * 2_500)
    assert res.P0_N == pytest.approx(expected_P0)
    assert res.S0 == pytest.approx(6_600 / expected_P0, rel=1e-9)


# --------------------------------------------------------------------------- #
# Validation                                                                   #
# --------------------------------------------------------------------------- #
def test_C0_zero_with_axial_ball_raises():
    with pytest.raises(ValueError, match="C0_N"):
        calculate_bearing(
            C_N=20_000, C0_N=0,
            Fr_N=3_000, Fa_N=1_500,
            n_rpm=1_500,
            bearing_type=BearingType.BALL_RADIAL,
        )


def test_zero_loads_rejected():
    with pytest.raises(ValueError):
        calculate_bearing(
            C_N=20_000, C0_N=10_000,
            Fr_N=0, Fa_N=0,
            n_rpm=1_500,
            bearing_type=BearingType.BALL_RADIAL,
        )


def test_negative_speed_rejected():
    with pytest.raises(ValueError):
        calculate_bearing(
            C_N=20_000, C0_N=10_000,
            Fr_N=2_000, Fa_N=0,
            n_rpm=-1,
            bearing_type=BearingType.BALL_RADIAL,
        )


def test_negative_C_rejected():
    with pytest.raises(ValueError):
        calculate_bearing(
            C_N=-1, C0_N=10_000,
            Fr_N=2_000, Fa_N=0, n_rpm=1_500,
            bearing_type=BearingType.BALL_RADIAL,
        )


# --------------------------------------------------------------------------- #
# Required C (inverse formula) and catalog optimization                        #
# --------------------------------------------------------------------------- #
def test_required_C_is_inverse_of_L10():
    Fr, Fa, n, target = 3_000.0, 0.0, 1_500.0, 10_000.0
    P, _e, _X, _Y = equivalent_load_dynamic(
        Fr, Fa, C0_N=0, bearing_type=BearingType.BALL_RADIAL,
    )
    C = required_C(P, n, target, BearingType.BALL_RADIAL)
    res = calculate_bearing(
        C_N=C, C0_N=10_000,
        Fr_N=Fr, Fa_N=Fa, n_rpm=n,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=target,
    )
    assert res.L10_hours == pytest.approx(target, rel=1e-9)


def test_optimize_picks_smallest_catalog_entry():
    res = optimize_bearing(
        Fr_N=3_000, Fa_N=0, n_rpm=1_500,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=20_000,
        catalog=DEFAULT_BALL_BEARING_CATALOG,
    )
    assert res.found is True
    assert res.optimal is not None
    assert res.optimal.C_N >= res.C_required_N
    assert res.optimal.C0_N >= res.C0_required_N

    # Lighter entries fail at least one of the two criteria
    for e in res.evaluations:
        if e.entry.C_N < res.optimal.C_N:
            assert e.status_dyn == "Insuffisant" or e.status_stat == "Insuffisant"


def test_optimize_no_solution_when_target_huge():
    res = optimize_bearing(
        Fr_N=50_000, Fa_N=0, n_rpm=3_000,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=100_000,
        catalog=DEFAULT_BALL_BEARING_CATALOG,
    )
    assert res.found is False
    assert res.optimal is None
    assert math.isfinite(res.C_required_N) and res.C_required_N > 0
    assert math.isfinite(res.C0_required_N) and res.C0_required_N > 0


# --------------------------------------------------------------------------- #
# Étape 12 — Nouveaux types : oblique, 2 rangées, conique                       #
# --------------------------------------------------------------------------- #
from core.bearing import (
    BearingSetResult,
    OBLIQUE_BALL_TABLE,
    VariableLoadPeriod,
    calculate_bearing_set,
    calculate_variable_load,
    oblique_ball_xye,
)


def test_oblique_xye_table_values():
    assert OBLIQUE_BALL_TABLE[15] == (1.14, 0.35, 0.57)
    assert OBLIQUE_BALL_TABLE[20] == (0.80, 0.39, 0.76)
    assert OBLIQUE_BALL_TABLE[25] == (0.95, 0.37, 0.66)
    assert OBLIQUE_BALL_TABLE[30] == (0.80, 0.35, 0.57)


def test_oblique_xye_nearest_angle():
    # α=17° → choisit 15° (le plus proche)
    e, X, Y = oblique_ball_xye(17)
    assert (e, X, Y) == (1.14, 0.35, 0.57)
    # α=23° → choisit 25° (le plus proche)
    e, X, Y = oblique_ball_xye(23)
    assert (e, X, Y) == (0.95, 0.37, 0.66)


def test_oblique_15deg_above_threshold():
    """α=15°, Fa/Fr=1.5 > e=1.14 → P = 0.35·Fr + 0.57·Fa."""
    res = calculate_bearing(
        C_N=20_000, C0_N=10_000,
        Fr_N=10_000, Fa_N=15_000,   # ratio 1.5 > 1.14
        n_rpm=1_000,
        bearing_type=BearingType.BALL_OBLIQUE_1ROW,
        alpha_deg=15,
    )
    expected_P = 0.35 * 10_000 + 0.57 * 15_000   # = 12 050 N
    assert res.X_used == pytest.approx(0.35)
    assert res.Y_used == pytest.approx(0.57)
    assert res.P_N == pytest.approx(expected_P, rel=1e-9)


def test_oblique_15deg_below_threshold():
    """α=15°, Fa/Fr=1.0 < e=1.14 → P = Fr (X=1, Y=0)."""
    res = calculate_bearing(
        C_N=20_000, C0_N=10_000,
        Fr_N=10_000, Fa_N=10_000,   # ratio 1.0 < 1.14
        n_rpm=1_000,
        bearing_type=BearingType.BALL_OBLIQUE_1ROW,
        alpha_deg=15,
    )
    assert res.X_used == pytest.approx(1.0)
    assert res.Y_used == pytest.approx(0.0)
    assert res.P_N == pytest.approx(10_000)


def test_oblique_requires_alpha():
    with pytest.raises(ValueError, match="alpha_deg"):
        calculate_bearing(
            C_N=20_000, C0_N=10_000,
            Fr_N=10_000, Fa_N=5_000, n_rpm=1_000,
            bearing_type=BearingType.BALL_OBLIQUE_1ROW,
        )


def test_roller_conical_above_threshold():
    """Fa/Fr=0.6 > e=0.4 → P = 0.4·Fr + Y·Fa."""
    res = calculate_bearing(
        C_N=50_000, C0_N=50_000,
        Fr_N=10_000, Fa_N=6_000,    # ratio 0.6 > 0.4
        n_rpm=1_000,
        bearing_type=BearingType.ROLLER_CONICAL,
        Y_conical=1.5, e_conical=0.4,
    )
    expected_P = 0.40 * 10_000 + 1.5 * 6_000     # = 13 000 N
    assert res.P_N == pytest.approx(expected_P, rel=1e-9)


def test_roller_conical_below_threshold():
    res = calculate_bearing(
        C_N=50_000, C0_N=50_000,
        Fr_N=10_000, Fa_N=2_000,    # ratio 0.2 < 0.4
        n_rpm=1_000,
        bearing_type=BearingType.ROLLER_CONICAL,
    )
    assert res.P_N == pytest.approx(10_000)


def test_ball_radial_1row_is_equivalent_to_ball_radial():
    """BALL_RADIAL_1ROW doit produire les mêmes résultats que BALL_RADIAL."""
    common = dict(
        C_N=12_800, C0_N=6_600,
        Fr_N=4_000, Fa_N=2_500, n_rpm=200, target_hours=20_000,
    )
    r1 = calculate_bearing(bearing_type=BearingType.BALL_RADIAL, **common)
    r2 = calculate_bearing(bearing_type=BearingType.BALL_RADIAL_1ROW, **common)
    assert r1.P_N == pytest.approx(r2.P_N, rel=1e-12)
    assert r1.L10_hours == pytest.approx(r2.L10_hours, rel=1e-12)


# --------------------------------------------------------------------------- #
# LE10 — ensemble de roulements                                                #
# --------------------------------------------------------------------------- #
def _result_with_L10h(L10h: float) -> "BearingResult":
    """Construit un BearingResult artificiel dont le L10_hours vaut L10h."""
    # On choisit Fr et n simples, et on règle C tel que L10h = (C/Fr)^3 × 1e6 / (60 n).
    # → C = Fr × (L10h × 60 × n / 1e6)^(1/3)
    Fr = 1_000.0
    n = 100.0
    C = Fr * (L10h * 60 * n / 1e6) ** (1 / 3)
    return calculate_bearing(
        C_N=C, C0_N=C,
        Fr_N=Fr, Fa_N=0, n_rpm=n,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=L10h,
    )


def test_LE10_cours_example_15000_25000_hours():
    """LE10 de deux roulements à 15000h et 25000h ≈ 11630h (cours AP27)."""
    r1 = _result_with_L10h(15_000)
    r2 = _result_with_L10h(25_000)
    s = calculate_bearing_set([r1, r2])
    assert s.LE10_hours == pytest.approx(11630, rel=0.01)
    # Le goulot est r1 (15000 < 25000)
    assert s.weakest_index == 0
    assert s.weakest_L10_hours == pytest.approx(15_000, rel=1e-3)


def test_LE10_single_bearing_equals_its_L10():
    """Un ensemble d'1 seul roulement → LE10 = L10."""
    r = _result_with_L10h(20_000)
    s = calculate_bearing_set([r])
    assert s.LE10_hours == pytest.approx(20_000, rel=1e-3)


def test_LE10_empty_set_raises():
    with pytest.raises(ValueError):
        calculate_bearing_set([])


# --------------------------------------------------------------------------- #
# Chargement variable                                                          #
# --------------------------------------------------------------------------- #
def test_variable_load_50_50_ball():
    """50% × 10kN + 50% × 5kN, billes → Pe = (0.5×10000³ + 0.5×5000³)^(1/3) ≈ 8254 N."""
    res = calculate_variable_load(
        periods=[
            VariableLoadPeriod(P_N=10_000, a_fraction=0.5),
            VariableLoadPeriod(P_N=5_000,  a_fraction=0.5),
        ],
        bearing_type=BearingType.BALL_RADIAL,
    )
    expected = (0.5 * 10_000 ** 3 + 0.5 * 5_000 ** 3) ** (1 / 3)
    assert res.Pe_N == pytest.approx(expected, rel=1e-9)
    assert res.n_exponent == pytest.approx(3.0)


def test_variable_load_uses_roller_exponent():
    res = calculate_variable_load(
        periods=[
            VariableLoadPeriod(P_N=10_000, a_fraction=1.0),
        ],
        bearing_type=BearingType.ROLLER_CYLINDRICAL,
    )
    assert res.n_exponent == pytest.approx(10 / 3)
    assert res.Pe_N == pytest.approx(10_000)


def test_variable_load_sum_not_1_raises():
    with pytest.raises(ValueError, match="a_fraction"):
        calculate_variable_load(
            periods=[
                VariableLoadPeriod(P_N=10_000, a_fraction=0.3),
                VariableLoadPeriod(P_N=5_000,  a_fraction=0.5),
            ],
            bearing_type=BearingType.BALL_RADIAL,
        )


def test_variable_load_empty_periods_raises():
    with pytest.raises(ValueError):
        calculate_variable_load([], bearing_type=BearingType.BALL_RADIAL)


# --------------------------------------------------------------------------- #
# Real catalog — optimize_bearing_catalog                                      #
# --------------------------------------------------------------------------- #
from core.bearing_catalog import (
    REAL_BEARING_CATALOG,
    optimize_bearing_catalog,
)


def test_real_catalog_contains_AP27_references():
    designations = {e.designation for e in REAL_BEARING_CATALOG}
    # Quelques références emblématiques du cours
    for ref in ["6203", "6204", "6205", "6304", "6406", "6408"]:
        assert ref in designations


def test_optimize_real_catalog_ap27_exo1():
    """Cours AP27 exo1 : Fr=4000N, Fa=2500N, n=200rpm, cible 5000h, d=20mm.

    Vérifie que le roulement retourné a L10h ≥ 5000h.
    """
    res = optimize_bearing_catalog(
        Fr_N=4_000, Fa_N=2_500,
        C0_estimate_N=6_600,        # estimation initiale (ex. 6204)
        n_rpm=200,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=5_000,
        d_arbre_mm=20,
    )
    assert res.found is True
    assert res.optimal is not None
    assert res.result is not None
    assert res.result.L10_hours >= 5_000
    assert res.optimal.d_bore_mm == 20


def test_optimize_real_catalog_no_filter_searches_whole_catalog():
    res = optimize_bearing_catalog(
        Fr_N=4_000, Fa_N=2_500,
        C0_estimate_N=6_600,
        n_rpm=200,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=5_000,
    )
    assert res.found is True
    # Sans filtre, le minimum global (toutes tailles confondues) est sélectionné
    assert res.optimal is not None
    assert res.evaluations  # liste non vide


def test_optimize_real_catalog_no_solution():
    res = optimize_bearing_catalog(
        Fr_N=100_000, Fa_N=0,
        C0_estimate_N=50_000,
        n_rpm=3_000,
        bearing_type=BearingType.BALL_RADIAL,
        target_hours=100_000,
        d_arbre_mm=17,        # filtre étroit sur petits roulements
    )
    assert res.found is False
    assert res.optimal is None


def test_optimize_real_catalog_invalid_inputs():
    with pytest.raises(ValueError):
        optimize_bearing_catalog(
            Fr_N=0, Fa_N=0,
            C0_estimate_N=1_000, n_rpm=1_000,
            bearing_type=BearingType.BALL_RADIAL,
            target_hours=5_000,
        )
    with pytest.raises(ValueError):
        optimize_bearing_catalog(
            Fr_N=3_000, Fa_N=0,
            C0_estimate_N=0, n_rpm=1_000,
            bearing_type=BearingType.BALL_RADIAL,
            target_hours=5_000,
        )
