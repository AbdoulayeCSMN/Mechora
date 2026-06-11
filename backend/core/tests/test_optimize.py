"""Tests for the catalog-based optimizer."""

import pytest

from core.loads import PointLoad, SupportType
from core.materials import get_material
from core.optimize import optimize_beam_catalog
from core.profiles import IPE_CATALOG


S235 = get_material("S235")


def test_intermediate_profile_is_chosen():
    """SS beam, L=4m, P=10kN central, S235, Cs >= 2.0, f <= L/200.

    Hand check:
      M_max = PL/4 = 10 kN·m
      Required W (σ_allow = 235/2 = 117.5 MPa) = 10e3 / 117.5e6 = 85.1 cm³
      Required I (f_lim = 20 mm) = PL³/(48·E·f_lim) ≈ 317 cm⁴
      → smallest IPE satisfying both = IPE 160 (W=109, I=869).
    """
    res = optimize_beam_catalog(
        length=4.0,
        material=S235,
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=10_000.0, position=2.0)],
        target_safety_factor=2.0,
        catalog=IPE_CATALOG,
        deflection_ratio=200.0,
    )

    assert res.optimal is not None
    assert res.optimal.designation == "IPE 160"

    # All lighter profiles must be flagged as NOT OK
    lighter = [e for e in res.evaluations
               if e.profile.mass_kg_per_m < res.optimal.mass_kg_per_m]
    assert all(e.status != "OK" for e in lighter)
    assert len(lighter) >= 1


def test_no_solution_returns_none():
    """A 200 kN point load at midspan exceeds the strength of every IPE."""
    res = optimize_beam_catalog(
        length=4.0,
        material=S235,
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=200_000.0, position=2.0)],
        target_safety_factor=2.0,
        catalog=IPE_CATALOG,
        deflection_ratio=200.0,
    )

    assert res.optimal is None
    assert res.optimal_result is None
    assert all(e.status != "OK" for e in res.evaluations)
    assert len(res.evaluations) == len(IPE_CATALOG)


def test_optimal_profile_meets_both_criteria():
    """The chosen profile's BeamResult must satisfy Cs and deflection."""
    res = optimize_beam_catalog(
        length=4.0,
        material=S235,
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=10_000.0, position=2.0)],
        target_safety_factor=2.0,
        catalog=IPE_CATALOG,
        deflection_ratio=200.0,
    )

    assert res.optimal_result is not None
    assert res.optimal_result.Cs >= 2.0
    assert res.optimal_result.f_max <= res.deflection_limit_m


def test_heavier_target_pushes_optimum_up():
    """Doubling the target safety factor selects a heavier profile."""
    common = dict(
        length=4.0,
        material=S235,
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=10_000.0, position=2.0)],
        catalog=IPE_CATALOG,
        deflection_ratio=200.0,
    )
    light = optimize_beam_catalog(target_safety_factor=2.0, **common)
    heavy = optimize_beam_catalog(target_safety_factor=4.0, **common)

    assert light.optimal is not None and heavy.optimal is not None
    assert heavy.optimal.mass_kg_per_m >= light.optimal.mass_kg_per_m


def test_stricter_deflection_pushes_optimum_up():
    """Tightening deflection limit (L/300 instead of L/200) yields ≥ heavier."""
    common = dict(
        length=4.0,
        material=S235,
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=10_000.0, position=2.0)],
        target_safety_factor=2.0,
        catalog=IPE_CATALOG,
    )
    loose = optimize_beam_catalog(deflection_ratio=200.0, **common)
    tight = optimize_beam_catalog(deflection_ratio=500.0, **common)

    assert loose.optimal is not None and tight.optimal is not None
    assert tight.optimal.mass_kg_per_m >= loose.optimal.mass_kg_per_m


def test_invalid_target_raises():
    with pytest.raises(ValueError):
        optimize_beam_catalog(
            length=4.0,
            material=S235,
            support=SupportType.SIMPLY_SUPPORTED,
            loads=[PointLoad(magnitude=10_000.0, position=2.0)],
            target_safety_factor=0,
            catalog=IPE_CATALOG,
        )
