"""Tests for the parallel-key module."""

import math

import pytest
from pydantic import ValidationError

from core.key import (
    HubMaterial,
    KeySection,
    calculate_key,
    optimize_key,
    select_iso_key_section,
)
from core.materials import get_material


S235 = get_material("S235")
S355 = get_material("S355")


# --------------------------------------------------------------------------- #
# ISO 773 table                                                                #
# --------------------------------------------------------------------------- #
def test_iso_table_d25_picks_b8_h7():
    b, h = select_iso_key_section(25)
    assert (b, h) == (8, 7)


@pytest.mark.parametrize(
    "d, expected",
    [
        (7,  (2, 2)),   # in (6, 8]
        (8,  (2, 2)),   # boundary stays in lower bracket
        (10, (3, 3)),
        (12, (4, 4)),
        (50, (14, 9)),
        (75, (20, 12)),
    ],
)
def test_iso_table_other_ranges(d, expected):
    assert select_iso_key_section(d) == expected


def test_iso_table_above_range_raises():
    with pytest.raises(ValueError, match="above"):
        select_iso_key_section(76)


def test_iso_table_below_range_raises():
    with pytest.raises(ValueError, match="below"):
        select_iso_key_section(5)


# --------------------------------------------------------------------------- #
# Section / l_active validation                                                #
# --------------------------------------------------------------------------- #
def test_key_section_requires_l_total_above_b():
    with pytest.raises(ValidationError):
        KeySection(b=0.008, h=0.007, l_total=0.008)
    with pytest.raises(ValidationError):
        KeySection(b=0.008, h=0.007, l_total=0.005)


# --------------------------------------------------------------------------- #
# Stress formulas — verified numerically                                       #
# --------------------------------------------------------------------------- #
def test_shear_stress_formula():
    d = 0.025
    Mt = 80.0
    l_total = 0.040
    res = calculate_key(
        shaft_diameter_m=d,
        Mt_Nm=Mt,
        material_shaft=S235,
        hub_material=HubMaterial.STEEL,
        l_total_m=l_total,
    )
    b = res.section.b
    l_active = res.section.l_active
    expected_tau = 2 * Mt / (d * b * l_active)
    assert res.tau_Pa == pytest.approx(expected_tau, rel=1e-12)


def test_bearing_stress_formula():
    d = 0.025
    Mt = 80.0
    l_total = 0.040
    res = calculate_key(
        shaft_diameter_m=d,
        Mt_Nm=Mt,
        material_shaft=S235,
        hub_material=HubMaterial.STEEL,
        l_total_m=l_total,
    )
    h = res.section.h
    l_active = res.section.l_active
    expected_sigma_m = 4 * Mt / (d * h * l_active)
    assert res.sigma_m_Pa == pytest.approx(expected_sigma_m, rel=1e-12)


def test_shear_admissible_is_re_over_sqrt3():
    res = calculate_key(
        shaft_diameter_m=0.025,
        Mt_Nm=80.0,
        material_shaft=S235,
        hub_material=HubMaterial.STEEL,
        l_total_m=0.040,
    )
    assert res.Re_shear_Pa == pytest.approx(S235.Re / math.sqrt(3), rel=1e-12)


def test_bearing_admissible_per_hub_material():
    base = dict(
        shaft_diameter_m=0.025,
        Mt_Nm=80.0,
        material_shaft=S235,
        l_total_m=0.040,
    )
    steel = calculate_key(hub_material=HubMaterial.STEEL, **base)
    cast = calculate_key(hub_material=HubMaterial.CAST_IRON, **base)
    alu = calculate_key(hub_material=HubMaterial.ALUMINUM, **base)
    assert steel.sigma_m_adm_Pa == pytest.approx(150e6)
    assert cast.sigma_m_adm_Pa == pytest.approx(80e6)
    assert alu.sigma_m_adm_Pa == pytest.approx(60e6)


# --------------------------------------------------------------------------- #
# Verdict + limiting criterion                                                 #
# --------------------------------------------------------------------------- #
def test_short_key_underdesigned():
    # d=25mm → b=8mm. l_total very short → l_active = 12 - 8 = 4 mm, huge τ
    res = calculate_key(
        shaft_diameter_m=0.025,
        Mt_Nm=300.0,
        material_shaft=S235,
        hub_material=HubMaterial.ALUMINUM,
        l_total_m=0.012,
    )
    assert res.verdict == "Sous-dimensionné"
    assert res.Cs < 1.0


def test_limiting_is_bearing_for_alu_hub():
    # σ_m_adm = 60 MPa (alu) is the weakest. Pick numbers so bearing fails first.
    res = calculate_key(
        shaft_diameter_m=0.025,
        Mt_Nm=120.0,
        material_shaft=S235,
        hub_material=HubMaterial.ALUMINUM,
        l_total_m=0.025,
    )
    # Aluminium hub → bearing is much more constrained than shear.
    assert res.Cs_bearing < res.Cs_shear
    assert res.limiting_criterion == "matage"


def test_mt_zero_rejected():
    with pytest.raises(ValueError):
        calculate_key(
            shaft_diameter_m=0.025,
            Mt_Nm=0,
            material_shaft=S235,
            hub_material=HubMaterial.STEEL,
            l_total_m=0.040,
        )


# --------------------------------------------------------------------------- #
# Optimization                                                                 #
# --------------------------------------------------------------------------- #
def test_optimize_returns_length_meeting_target():
    res = optimize_key(
        shaft_diameter_m=0.025,
        Mt_Nm=120.0,
        material_shaft=S235,
        hub_material=HubMaterial.STEEL,
        target_cs=2.0,
    )
    assert res.found is True
    assert res.l_total_optimal_m is not None
    assert res.result is not None
    assert res.result.Cs >= 2.0


def test_optimize_no_solution_returns_not_found():
    # Massive torque on aluminium hub, tiny diameter → no length works
    res = optimize_key(
        shaft_diameter_m=0.012,
        Mt_Nm=5_000.0,
        material_shaft=S235,
        hub_material=HubMaterial.ALUMINUM,
        target_cs=2.0,
        l_max_mm=50,
    )
    assert res.found is False
    assert res.l_total_optimal_m is None


def test_optimize_invalid_target_raises():
    with pytest.raises(ValueError):
        optimize_key(
            shaft_diameter_m=0.025,
            Mt_Nm=120.0,
            material_shaft=S235,
            hub_material=HubMaterial.STEEL,
            target_cs=0,
        )
