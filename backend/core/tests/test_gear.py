"""Tests for the spur gear module (Lewis bending + Hertz contact)."""

import math

import pytest

from core.gear import (
    ISO_MODULE_SERIES_MM,
    LEWIS_FORM_FACTOR_TABLE,
    calculate_gear,
    elasticity_factor,
    lewis_form_factor,
    optimize_gear,
)
from core.materials import get_material


S235 = get_material("S235")
S355 = get_material("S355")
C45E = get_material("C45E")


# --------------------------------------------------------------------------- #
# Lewis form factor table                                                      #
# --------------------------------------------------------------------------- #
def test_lewis_form_factor_exact_table_values():
    for z, y in LEWIS_FORM_FACTOR_TABLE:
        assert lewis_form_factor(z) == pytest.approx(y)


def test_lewis_form_factor_interpolates_between_entries():
    y12, y13 = lewis_form_factor(12), lewis_form_factor(13)
    y_mid = lewis_form_factor(12)  # exact value at 12
    assert y_mid == pytest.approx(y12)
    # interpolation strictly between 12 and 13 increases monotonically
    assert y13 > y12


def test_lewis_form_factor_below_minimum_raises():
    with pytest.raises(ValueError, match="below"):
        lewis_form_factor(11)


def test_lewis_form_factor_clamped_above_table():
    assert lewis_form_factor(2000) == LEWIS_FORM_FACTOR_TABLE[-1][1]


# --------------------------------------------------------------------------- #
# Elasticity factor                                                            #
# --------------------------------------------------------------------------- #
def test_elasticity_factor_steel_steel_close_to_iso_value():
    z_e = elasticity_factor(S235, S235)
    # ISO 6336 reference value for steel/steel ≈ 189.8 sqrt(MPa) = 189.8e3 sqrt(Pa)
    assert z_e == pytest.approx(191.6e3, rel=2e-2)


# --------------------------------------------------------------------------- #
# Geometry                                                                     #
# --------------------------------------------------------------------------- #
def test_geometry_derived_quantities():
    res = calculate_gear(
        m_m=0.003,
        z1=20,
        z2=40,
        b_m=0.030,
        Mt1_Nm=50.0,
        n1_rpm=1000.0,
        material_pinion=S235,
        material_gear=S235,
    )
    g = res.geometry
    assert g.d1 == pytest.approx(0.003 * 20)
    assert g.d2 == pytest.approx(0.003 * 40)
    assert g.a == pytest.approx((g.d1 + g.d2) / 2)
    assert g.u == pytest.approx(2.0)


# --------------------------------------------------------------------------- #
# Forces & stresses — verified numerically                                     #
# --------------------------------------------------------------------------- #
def test_tangential_force_formula():
    m, z1, Mt1 = 0.003, 20, 50.0
    res = calculate_gear(
        m_m=m, z1=z1, z2=40, b_m=0.030, Mt1_Nm=Mt1, n1_rpm=1000.0,
        material_pinion=S235, material_gear=S235,
    )
    d1 = m * z1
    expected_Ft = 2.0 * Mt1 / d1
    assert res.Ft_N == pytest.approx(expected_Ft, rel=1e-12)
    assert res.Fr_N == pytest.approx(expected_Ft * math.tan(math.radians(20.0)), rel=1e-12)


def test_bending_stress_formula():
    m, z1, z2, b, Mt1, n1 = 0.003, 20, 40, 0.030, 50.0, 1000.0
    res = calculate_gear(
        m_m=m, z1=z1, z2=z2, b_m=b, Mt1_Nm=Mt1, n1_rpm=n1,
        material_pinion=S235, material_gear=S235, K_A=1.2,
    )
    d1 = m * z1
    Ft = 2.0 * Mt1 / d1
    v = math.pi * d1 * n1 / 60.0
    Kv = 1.0 + v / 6.0
    YF1 = lewis_form_factor(z1)
    expected_sigma_F1 = (Ft * 1.2 * Kv / (b * m)) * YF1
    assert res.sigma_F1_Pa == pytest.approx(expected_sigma_F1, rel=1e-12)
    assert res.K_V == pytest.approx(Kv, rel=1e-12)


def test_contact_stress_formula():
    m, z1, z2, b, Mt1, n1 = 0.003, 20, 40, 0.030, 50.0, 1000.0
    res = calculate_gear(
        m_m=m, z1=z1, z2=z2, b_m=b, Mt1_Nm=Mt1, n1_rpm=n1,
        material_pinion=S235, material_gear=S235,
    )
    d1 = m * z1
    u = z2 / z1
    Ft = 2.0 * Mt1 / d1
    v = math.pi * d1 * n1 / 60.0
    Kv = 1.0 + v / 6.0
    Z_E = elasticity_factor(S235, S235)
    expected_sigma_H = Z_E * math.sqrt((Ft * 1.0 * Kv / (b * d1)) * ((u + 1.0) / u))
    assert res.sigma_H_Pa == pytest.approx(expected_sigma_H, rel=1e-12)


def test_admissible_stresses_from_materials():
    res = calculate_gear(
        m_m=0.003, z1=20, z2=40, b_m=0.030, Mt1_Nm=50.0, n1_rpm=1000.0,
        material_pinion=S235, material_gear=S355,
    )
    assert res.sigma_F1_adm_Pa == pytest.approx(S235.sigma_D)
    assert res.sigma_F2_adm_Pa == pytest.approx(S355.sigma_D)
    assert res.sigma_H_adm_Pa == pytest.approx(min(S235.sigma_H_lim, S355.sigma_H_lim))


# --------------------------------------------------------------------------- #
# Verdict + limiting criterion                                                 #
# --------------------------------------------------------------------------- #
def test_undersized_gear_is_underdesigned():
    # Tiny module, huge torque -> very high stresses
    res = calculate_gear(
        m_m=0.001, z1=12, z2=48, b_m=0.005, Mt1_Nm=200.0, n1_rpm=1500.0,
        material_pinion=S235, material_gear=S235,
    )
    assert res.verdict == "Sous-dimensionné"
    assert res.Cs < 1.0
    assert res.limiting_criterion in {
        "flexion_pignon", "flexion_roue", "pression_superficielle",
    }


def test_oversized_gear_is_oversized():
    res = calculate_gear(
        m_m=0.010, z1=30, z2=60, b_m=0.100, Mt1_Nm=20.0, n1_rpm=200.0,
        material_pinion=C45E, material_gear=C45E,
    )
    assert res.verdict == "Surdimensionné"
    assert res.Cs > 4.0


def test_invalid_inputs_raise():
    base = dict(
        m_m=0.003, z1=20, z2=40, b_m=0.030, Mt1_Nm=50.0, n1_rpm=1000.0,
        material_pinion=S235, material_gear=S235,
    )
    with pytest.raises(ValueError):
        calculate_gear(**{**base, "m_m": 0})
    with pytest.raises(ValueError):
        calculate_gear(**{**base, "Mt1_Nm": 0})
    with pytest.raises(ValueError):
        calculate_gear(**{**base, "n1_rpm": 0})
    with pytest.raises(ValueError):
        calculate_gear(**{**base, "K_A": 0})


def test_z_below_minimum_rejected():
    with pytest.raises(ValueError):
        calculate_gear(
            m_m=0.003, z1=10, z2=40, b_m=0.030, Mt1_Nm=50.0, n1_rpm=1000.0,
            material_pinion=S235, material_gear=S235,
        )


# --------------------------------------------------------------------------- #
# Optimization                                                                 #
# --------------------------------------------------------------------------- #
def test_optimize_returns_module_meeting_target():
    res = optimize_gear(
        z1=20, z2=40, Mt1_Nm=50.0, n1_rpm=1000.0,
        material_pinion=S235, material_gear=S235, target_cs=1.5,
    )
    assert res.found is True
    assert res.m_optimal_mm in ISO_MODULE_SERIES_MM
    assert res.result is not None
    assert res.result.Cs >= 1.5


def test_optimize_no_solution_returns_not_found():
    res = optimize_gear(
        z1=12, z2=12, Mt1_Nm=50_000.0, n1_rpm=3000.0,
        material_pinion=S235, material_gear=S235, target_cs=2.0,
        module_series_mm=[1.0, 2.0],
    )
    assert res.found is False
    assert res.m_optimal_mm is None
    assert len(res.evaluations) == 2


def test_optimize_invalid_target_raises():
    with pytest.raises(ValueError):
        optimize_gear(
            z1=20, z2=40, Mt1_Nm=50.0, n1_rpm=1000.0,
            material_pinion=S235, material_gear=S235, target_cs=0,
        )
