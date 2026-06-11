"""Tests for the profile catalogues (IPE + HEA + HEB + UPN + SHS + CHS)."""

import pytest

from core.materials import get_material
from core.optimize import optimize_beam_catalog
from core.loads import PointLoad, SupportType
from core.profiles import (
    CATALOGS,
    CatalogProfile,
    HEA_CATALOG,
    HEB_CATALOG,
    IPE_CATALOG,
    UPN_CATALOG,
    SHS_CATALOG,
    CHS_CATALOG,
    get_all_catalogs,
    get_catalog,
    get_combined_catalog,
)


S235 = get_material("S235")


# --------------------------------------------------------------------------- #
# IPE (étape 4)                                                                #
# --------------------------------------------------------------------------- #
def test_ipe_catalog_has_expected_profiles():
    names = [p.designation for p in IPE_CATALOG]
    expected = [
        "IPE 80", "IPE 100", "IPE 120", "IPE 140",
        "IPE 160", "IPE 180", "IPE 200", "IPE 220", "IPE 240",
    ]
    assert names == expected


def test_ipe_catalog_sorted_by_mass():
    masses = [p.mass_kg_per_m for p in IPE_CATALOG]
    assert masses == sorted(masses)


@pytest.mark.parametrize(
    "designation, h, Wy_cm3, Iy_cm4, mass",
    [
        ("IPE 80",  80.0,  20.0,  80.1,   6.0),
        ("IPE 160", 160.0, 109.0, 869.0,  15.8),
        ("IPE 240", 240.0, 324.0, 3892.0, 30.7),
    ],
)
def test_ipe_tabulated_values(designation, h, Wy_cm3, Iy_cm4, mass):
    p = next(x for x in IPE_CATALOG if x.designation == designation)
    assert p.h_mm == pytest.approx(h)
    assert p.Wy_cm3 == pytest.approx(Wy_cm3)
    assert p.Iy_cm4 == pytest.approx(Iy_cm4)
    assert p.mass_kg_per_m == pytest.approx(mass)


def test_si_properties_consistent_with_tabular():
    p = next(x for x in IPE_CATALOG if x.designation == "IPE 160")
    assert p.area == pytest.approx(20.1e-4)
    assert p.inertia == pytest.approx(869.0e-8)
    assert p.section_modulus == pytest.approx(109.0e-6)
    assert p.extreme_fiber == pytest.approx(0.08)


def test_mass_consistent_with_steel_density_ipe():
    rho = 7850.0
    for p in IPE_CATALOG:
        expected = p.area * rho
        assert p.mass_kg_per_m == pytest.approx(expected, rel=0.01)


def test_get_catalog_known_ipe():
    cat = get_catalog("IPE")
    assert cat is IPE_CATALOG
    assert "IPE" in CATALOGS


def test_get_catalog_unknown_raises():
    with pytest.raises(ValueError, match="unknown profile catalog"):
        get_catalog("XYZ")


def test_profile_negative_field_rejected():
    with pytest.raises(Exception):
        CatalogProfile(
            family="IPE", designation="bad",
            h_mm=-1, b_mm=46, area_cm2=7.64,
            Iy_cm4=80.1, Wy_cm3=20.0, mass_kg_per_m=6.0,
        )


# --------------------------------------------------------------------------- #
# HEA / HEB / UPN — valeurs ponctuelles                                        #
# --------------------------------------------------------------------------- #
def test_hea_200_reference_values():
    p = next(x for x in HEA_CATALOG if x.designation == "HEA 200")
    assert p.h_mm == pytest.approx(190)
    assert p.b_mm == pytest.approx(200)
    assert p.Wy_cm3 == pytest.approx(389)
    assert p.mass_kg_per_m == pytest.approx(42.3)


def test_heb_300_reference_values():
    p = next(x for x in HEB_CATALOG if x.designation == "HEB 300")
    assert p.Iy_cm4 == pytest.approx(25170)
    assert p.Wy_cm3 == pytest.approx(1678)


def test_upn_160_reference_values():
    p = next(x for x in UPN_CATALOG if x.designation == "UPN 160")
    assert p.Wy_cm3 == pytest.approx(116)
    assert p.h_mm == pytest.approx(160)
    assert p.b_mm == pytest.approx(65)


def test_shs_100x5_reference_values():
    p = next(x for x in SHS_CATALOG if x.designation == "SHS 100×5")
    assert p.Wy_cm3 == pytest.approx(58.2)
    assert p.area_cm2 == pytest.approx(18.5)


def test_chs_60_3x4_reference_values():
    p = next(x for x in CHS_CATALOG if x.designation == "CHS 60.3×4")
    assert p.Iy_cm4 == pytest.approx(31.0)
    assert p.Wy_cm3 == pytest.approx(10.3)


# --------------------------------------------------------------------------- #
# Sorted by mass within each catalogue                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "catalog",
    [IPE_CATALOG, HEA_CATALOG, HEB_CATALOG, UPN_CATALOG, SHS_CATALOG, CHS_CATALOG],
)
def test_each_catalog_sorted_by_mass(catalog):
    masses = [p.mass_kg_per_m for p in catalog]
    assert masses == sorted(masses), \
        f"{catalog[0].family} catalogue isn't sorted by mass"


# --------------------------------------------------------------------------- #
# Registry helpers                                                             #
# --------------------------------------------------------------------------- #
def test_get_catalog_returns_non_empty_for_all_families():
    for fam in ["IPE", "HEA", "HEB", "UPN", "SHS", "CHS"]:
        cat = get_catalog(fam)
        assert len(cat) >= 8


def test_get_all_catalogs_returns_six_families():
    all_cats = get_all_catalogs()
    assert set(all_cats) == {"IPE", "HEA", "HEB", "UPN", "SHS", "CHS"}


def test_get_combined_catalog_default_is_all_families():
    combined = get_combined_catalog()
    expected_total = sum(len(c) for c in CATALOGS.values())
    assert len(combined) == expected_total
    # Sorted by mass
    masses = [p.mass_kg_per_m for p in combined]
    assert masses == sorted(masses)


def test_get_combined_catalog_ipe_plus_hea_sorted_and_no_duplicates():
    combined = get_combined_catalog(["IPE", "HEA"])
    assert len(combined) == len(IPE_CATALOG) + len(HEA_CATALOG)
    # No duplicate (designation, family) pairs
    keys = [(p.family, p.designation) for p in combined]
    assert len(keys) == len(set(keys))
    # Sorted by mass
    masses = [p.mass_kg_per_m for p in combined]
    assert masses == sorted(masses)
    # Both families represented
    families = {p.family for p in combined}
    assert families == {"IPE", "HEA"}


def test_get_combined_catalog_unknown_family_raises():
    with pytest.raises(ValueError, match="unknown"):
        get_combined_catalog(["IPE", "WHATEVER"])


# --------------------------------------------------------------------------- #
# Optimization on the combined IPE + HEA catalog                               #
# --------------------------------------------------------------------------- #
def test_optimize_on_combined_catalog_picks_overall_lightest():
    """Optimising on IPE + HEA simultaneously must consider both."""
    combined = get_combined_catalog(["IPE", "HEA"])
    res = optimize_beam_catalog(
        length=4.0,
        material=S235,
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=10_000.0, position=2.0)],
        target_safety_factor=2.0,
        catalog=combined,
        deflection_ratio=200.0,
    )
    assert res.optimal is not None
    assert res.optimal_result is not None
    # The chosen one must actually satisfy the criteria
    assert res.optimal_result.Cs >= 2.0
    assert res.optimal_result.f_max <= res.deflection_limit_m

    # All evaluations strictly lighter than the optimum must fail at least one
    # of the two criteria (proves it's truly the lightest fit)
    lighter = [e for e in res.evaluations
               if e.profile.mass_kg_per_m < res.optimal.mass_kg_per_m]
    assert all(e.status != "OK" for e in lighter)


def test_optimize_on_chs_only_catalog():
    """The optimizer must also handle a single non-IPE family alone."""
    res = optimize_beam_catalog(
        length=2.0,
        material=S235,
        support=SupportType.CANTILEVER,
        loads=[PointLoad(magnitude=500.0, position=2.0)],
        target_safety_factor=2.0,
        catalog=CHS_CATALOG,
        deflection_ratio=150.0,
    )
    # We don't assert a specific profile, just that the result is well-formed
    if res.optimal is not None:
        assert res.optimal.family == "CHS"
        assert res.optimal_result is not None
        assert res.optimal_result.Cs >= 2.0
