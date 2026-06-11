import pytest

from core import units


def test_length_round_trip():
    assert units.mm_to_m(1000) == pytest.approx(1.0)
    assert units.m_to_mm(1.0) == pytest.approx(1000)
    assert units.cm_to_m(100) == pytest.approx(1.0)


def test_stress_conversions():
    assert units.mpa_to_pa(235) == pytest.approx(235e6)
    assert units.gpa_to_pa(210) == pytest.approx(210e9)
    assert units.pa_to_mpa(235e6) == pytest.approx(235)


def test_force_conversions():
    assert units.kn_to_n(5) == pytest.approx(5000)
    assert units.kgf_to_n(1) == pytest.approx(units.G)
