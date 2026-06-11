"""Tests for the shaft module."""

import math

import pytest
from pydantic import ValidationError

from core.materials import get_material
from core.optimize import optimize_shaft
from core.shaft import ShaftSection, calculate_shaft


S235 = get_material("S235")
S355 = get_material("S355")


# --------------------------------------------------------------------------- #
# Section moduli                                                               #
# --------------------------------------------------------------------------- #
def test_solid_section_moduli():
    d = 0.05  # 50 mm
    s = ShaftSection(type="solid", d_ext=d)
    assert s.W_f == pytest.approx(math.pi * d ** 3 / 32)
    assert s.W_t == pytest.approx(math.pi * d ** 3 / 16)
    assert s.W_t == pytest.approx(2 * s.W_f)
    assert s.area == pytest.approx(math.pi * d ** 2 / 4)


def test_hollow_section_moduli():
    D, d = 0.06, 0.04  # 60 / 40 mm
    s = ShaftSection(type="hollow", d_ext=D, d_int=d)
    assert s.W_f == pytest.approx(math.pi * (D ** 4 - d ** 4) / (32 * D))
    assert s.W_t == pytest.approx(math.pi * (D ** 4 - d ** 4) / (16 * D))
    assert s.area == pytest.approx(math.pi * (D ** 2 - d ** 2) / 4)


# --------------------------------------------------------------------------- #
# Limit cases for σ_eq                                                         #
# --------------------------------------------------------------------------- #
def test_bending_only_makes_tau_zero():
    section = ShaftSection(type="solid", d_ext=0.04)
    res = calculate_shaft(section, S235, Mf_Nm=200.0, Mt_Nm=0.0)
    assert res.tau_Pa == 0
    assert res.sigma_eq_Pa == pytest.approx(res.sigma_f_Pa, rel=1e-12)


def test_torsion_only_gives_sqrt3_times_tau():
    section = ShaftSection(type="solid", d_ext=0.04)
    res = calculate_shaft(section, S235, Mf_Nm=0.0, Mt_Nm=150.0)
    assert res.sigma_f_Pa == 0
    assert res.sigma_eq_Pa == pytest.approx(math.sqrt(3) * res.tau_Pa, rel=1e-12)


def test_combined_von_mises_formula():
    section = ShaftSection(type="solid", d_ext=0.04)
    Mf, Mt = 200.0, 150.0
    res = calculate_shaft(section, S235, Mf_Nm=Mf, Mt_Nm=Mt)
    sigma_f = Mf / section.W_f
    tau = Mt / section.W_t
    expected = math.sqrt(sigma_f ** 2 + 3 * tau ** 2)
    assert res.sigma_f_Pa == pytest.approx(sigma_f, rel=1e-12)
    assert res.tau_Pa == pytest.approx(tau, rel=1e-12)
    assert res.sigma_eq_Pa == pytest.approx(expected, rel=1e-12)


def test_safety_factor_propagation():
    section = ShaftSection(type="solid", d_ext=0.04)
    res = calculate_shaft(section, S235, Mf_Nm=100.0, Mt_Nm=80.0)
    assert res.Cs == pytest.approx(S235.Re / res.sigma_eq_Pa, rel=1e-12)


# --------------------------------------------------------------------------- #
# Validation errors                                                            #
# --------------------------------------------------------------------------- #
def test_inner_diameter_geq_outer_rejected():
    with pytest.raises(ValidationError):
        ShaftSection(type="hollow", d_ext=0.04, d_int=0.04)
    with pytest.raises(ValidationError):
        ShaftSection(type="hollow", d_ext=0.04, d_int=0.05)


def test_solid_must_have_zero_inner():
    with pytest.raises(ValidationError):
        ShaftSection(type="solid", d_ext=0.04, d_int=0.01)


def test_hollow_must_have_positive_inner():
    with pytest.raises(ValidationError):
        ShaftSection(type="hollow", d_ext=0.04, d_int=0.0)


def test_negative_outer_rejected():
    with pytest.raises(ValidationError):
        ShaftSection(type="solid", d_ext=-0.01)
    with pytest.raises(ValidationError):
        ShaftSection(type="solid", d_ext=0.0)


def test_both_moments_zero_rejected():
    section = ShaftSection(type="solid", d_ext=0.04)
    with pytest.raises(ValueError):
        calculate_shaft(section, S235, Mf_Nm=0.0, Mt_Nm=0.0)


def test_negative_moment_rejected():
    section = ShaftSection(type="solid", d_ext=0.04)
    with pytest.raises(ValueError):
        calculate_shaft(section, S235, Mf_Nm=-1.0, Mt_Nm=10.0)
    with pytest.raises(ValueError):
        calculate_shaft(section, S235, Mf_Nm=10.0, Mt_Nm=-1.0)


# --------------------------------------------------------------------------- #
# Optimization                                                                 #
# --------------------------------------------------------------------------- #
def test_optimize_returns_diameter_satisfying_cs():
    res = optimize_shaft(
        material=S235,
        Mf_Nm=200.0,
        Mt_Nm=150.0,
        shaft_type="solid",
        target_cs=2.0,
        d_min_mm=10,
        d_max_mm=80,
        step_mm=1,
    )
    assert res.found is True
    assert res.d_optimal_m is not None
    assert res.result is not None
    assert res.result.Cs >= 2.0

    # The diameter just below the optimum must NOT satisfy (proof of minimality)
    if res.d_optimal_m * 1e3 > 10:
        smaller = ShaftSection(
            type="solid", d_ext=res.d_optimal_m - 1e-3,
        )
        smaller_res = calculate_shaft(smaller, S235, Mf_Nm=200.0, Mt_Nm=150.0)
        assert smaller_res.Cs < 2.0


def test_optimize_no_solution_returns_not_found():
    # Massive moments, tiny diameter range → no solution
    res = optimize_shaft(
        material=S235,
        Mf_Nm=10_000.0,
        Mt_Nm=5_000.0,
        shaft_type="solid",
        target_cs=2.0,
        d_min_mm=10,
        d_max_mm=15,
        step_mm=1,
    )
    assert res.found is False
    assert res.d_optimal_m is None
    assert res.result is None


def test_optimize_hollow_uses_ratio():
    res = optimize_shaft(
        material=S235,
        Mf_Nm=300.0,
        Mt_Nm=200.0,
        shaft_type="hollow",
        target_cs=2.0,
        d_min_mm=20,
        d_max_mm=100,
        step_mm=1,
        d_int_ratio=0.7,
    )
    assert res.found is True
    assert res.result is not None
    assert res.result.section.type == "hollow"
    assert res.result.section.d_int == pytest.approx(
        res.result.section.d_ext * 0.7
    )


def test_optimize_invalid_target_raises():
    with pytest.raises(ValueError):
        optimize_shaft(
            material=S235, Mf_Nm=100, Mt_Nm=50,
            shaft_type="solid", target_cs=0,
        )


# --------------------------------------------------------------------------- #
# Advice integration                                                           #
# --------------------------------------------------------------------------- #
def test_underdesigned_shaft_advice_mentions_dominant_load():
    section = ShaftSection(type="solid", d_ext=0.010)  # 10 mm — too small
    res = calculate_shaft(section, S235, Mf_Nm=500.0, Mt_Nm=10.0)
    assert res.verdict == "Sous-dimensionné"
    assert res.advice.facteur_limitant == "contrainte"
    # bending dominates here → conseil should mention bending
    assert "flexion" in res.advice.conseil.lower()


def test_torsion_dominant_shaft_advice():
    section = ShaftSection(type="solid", d_ext=0.010)
    res = calculate_shaft(section, S235, Mf_Nm=10.0, Mt_Nm=500.0)
    assert res.verdict == "Sous-dimensionné"
    assert "torsion" in res.advice.conseil.lower()


def test_oversized_shaft_recommends_optimization():
    section = ShaftSection(type="solid", d_ext=0.1)  # 100 mm
    res = calculate_shaft(section, S235, Mf_Nm=10.0, Mt_Nm=5.0)
    assert res.verdict == "Surdimensionné"
    assert "optimisation" in res.advice.conseil.lower()
