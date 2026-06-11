"""Tests for the materials library."""

import pytest

from core.beam import Beam, analyze
from core.loads import PointLoad, SupportType
from core.materials import (
    FATIGUE_RATIO_BY_FAMILY,
    MATERIALS,
    Material,
    MaterialFamily,
    get_material,
    list_materials,
)
from core.sections import RectangularSection


# --------------------------------------------------------------------------- #
# Backward compatibility (tests existant à l'étape 1)                          #
# --------------------------------------------------------------------------- #
def test_known_materials_present():
    assert {"S235", "S355", "AL6060"}.issubset(set(MATERIALS))


def test_s235_values_si():
    m = get_material("S235")
    assert m.E == pytest.approx(210e9)
    assert m.Re == pytest.approx(235e6)


def test_unknown_material_raises():
    with pytest.raises(ValueError):
        get_material("Unobtanium")


def test_material_positive_validation():
    """Validation of E > 0 and Re > 0 (or None)."""
    with pytest.raises(Exception):
        Material(
            name="bad", family=MaterialFamily.STEEL,
            E=0, Re=100e6, Rm=200e6, density=7850,
        )
    with pytest.raises(Exception):
        Material(
            name="bad", family=MaterialFamily.STEEL,
            E=210e9, Re=-1, Rm=200e6, density=7850,
        )


# --------------------------------------------------------------------------- #
# Full catalogue presence (étape 10)                                           #
# --------------------------------------------------------------------------- #
EXPECTED_NAMES = {
    # Construction steels
    "S235", "S275", "S355", "S460",
    # Machine steels
    "C45", "C45E", "42CrMo4", "16NiCr6",
    # Stainless
    "304L", "316L",
    # Cast iron
    "FGL200", "FGS500",
    # Aluminium alloys
    "AU4G", "AS7G", "AL6060", "6061-T6", "7075-T6",
}


def test_all_expected_materials_present():
    missing = EXPECTED_NAMES - set(MATERIALS)
    assert not missing, f"missing materials: {missing}"


# --------------------------------------------------------------------------- #
# Reference values for a few key materials                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name, E, Re, Rm",
    [
        ("S355",    210e9, 355e6, 510e6),
        ("C45",     210e9, 390e6, 620e6),
        ("42CrMo4", 210e9, 650e6, 900e6),
        ("7075-T6",  72e9, 503e6, 572e6),
    ],
)
def test_reference_values(name, E, Re, Rm):
    m = get_material(name)
    assert m.E == pytest.approx(E)
    assert m.Re == pytest.approx(Re)
    assert m.Rm == pytest.approx(Rm)


# --------------------------------------------------------------------------- #
# Fatigue limit auto-derivation                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["S235", "S355", "C45", "42CrMo4", "16NiCr6"])
def test_sigma_D_steel_is_0_45_Rm(name):
    m = get_material(name)
    assert m.sigma_D == pytest.approx(0.45 * m.Rm, rel=1e-9)


def test_sigma_D_cast_iron_is_0_36_Rm():
    m = get_material("FGS500")
    assert m.sigma_D == pytest.approx(0.36 * m.Rm, rel=1e-9)


def test_sigma_D_aluminium_is_0_40_Rm():
    m = get_material("7075-T6")
    assert m.sigma_D == pytest.approx(0.40 * m.Rm, rel=1e-9)


def test_sigma_D_override_when_explicitly_set():
    m = Material(
        name="custom", family=MaterialFamily.STEEL,
        E=210e9, Re=400e6, Rm=600e6, density=7850,
        sigma_D=350e6,
    )
    assert m.sigma_D == pytest.approx(350e6)


# --------------------------------------------------------------------------- #
# Cast-iron special case (Re may be None)                                      #
# --------------------------------------------------------------------------- #
def test_fgl200_has_no_yield_but_has_Rm():
    m = get_material("FGL200")
    assert m.Re is None
    assert m.Rm == pytest.approx(200e6)


def test_Re_effective_falls_back_to_rm_over_3_when_Re_is_None():
    m = get_material("FGL200")
    assert m.Re_effective == pytest.approx(200e6 / 3, rel=1e-12)


def test_Re_effective_equals_Re_when_set():
    m = get_material("S235")
    assert m.Re_effective == pytest.approx(m.Re)


# --------------------------------------------------------------------------- #
# list_materials filtering                                                     #
# --------------------------------------------------------------------------- #
def test_list_materials_unfiltered_returns_full_catalogue():
    all_mats = list_materials()
    assert len(all_mats) == len(MATERIALS)
    assert set(m.name for m in all_mats) == set(MATERIALS)


def test_list_materials_filter_steel_excludes_others():
    steels = list_materials(family=MaterialFamily.STEEL)
    assert all(m.family == MaterialFamily.STEEL for m in steels)
    names = {m.name for m in steels}
    assert {"S235", "S355", "C45", "42CrMo4"}.issubset(names)
    assert "7075-T6" not in names
    assert "FGL200" not in names


def test_list_materials_filter_aluminium():
    al = list_materials(family=MaterialFamily.ALUMINUM)
    assert all(m.family == MaterialFamily.ALUMINUM for m in al)
    names = {m.name for m in al}
    assert {"AL6060", "AU4G", "AS7G", "6061-T6", "7075-T6"}.issubset(names)


def test_list_materials_filter_cast_iron():
    ci = list_materials(family=MaterialFamily.CAST_IRON)
    assert {m.name for m in ci} == {"FGL200", "FGS500"}


def test_list_materials_filter_stainless():
    ss = list_materials(family=MaterialFamily.STAINLESS)
    assert {m.name for m in ss} == {"304L", "316L"}


# --------------------------------------------------------------------------- #
# Custom material works with beam engine                                       #
# --------------------------------------------------------------------------- #
def test_custom_material_works_with_beam_engine():
    """A user-built Material (not in the registry) feeds analyze() fine."""
    custom = Material(
        name="MyAlloy", family=MaterialFamily.OTHER,
        E=120e9, Re=300e6, Rm=450e6, density=4500, poisson_ratio=0.32,
    )
    beam = Beam(
        length=2.0,
        material=custom,
        section=RectangularSection(width=0.05, height=0.10),
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=1000, position=1.0)],
    )
    result = analyze(beam)
    assert result.Cs > 0
    expected_cs = custom.Re_effective / result.sigma_max
    assert result.Cs == pytest.approx(expected_cs, rel=1e-9)


def test_fgl200_works_with_beam_engine_via_Re_effective():
    """FGL200 has Re=None — engine must use Re_effective = Rm/3."""
    cast = get_material("FGL200")
    beam = Beam(
        length=2.0,
        material=cast,
        section=RectangularSection(width=0.05, height=0.10),
        support=SupportType.SIMPLY_SUPPORTED,
        loads=[PointLoad(magnitude=500, position=1.0)],
    )
    result = analyze(beam)
    assert result.Cs > 0
    assert result.Cs == pytest.approx((200e6 / 3) / result.sigma_max, rel=1e-9)


# --------------------------------------------------------------------------- #
# Sanity checks on density / Poisson defaults                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name, density",
    [
        ("S355", 7850),
        ("AL6060", 2700),
        ("FGL200", 7200),
        ("304L", 7900),
    ],
)
def test_density_values(name, density):
    assert get_material(name).density == pytest.approx(density)


def test_poisson_ratio_steel_default_is_0_30():
    assert get_material("S355").poisson_ratio == pytest.approx(0.30)


def test_poisson_ratio_aluminium_is_0_33():
    assert get_material("AL6060").poisson_ratio == pytest.approx(0.33)


def test_fatigue_ratio_table_consistency():
    """sigma_D = family_ratio × Rm for every catalogue material."""
    for m in MATERIALS.values():
        if m.sigma_D is None:
            continue
        ratio = FATIGUE_RATIO_BY_FAMILY[m.family]
        assert m.sigma_D == pytest.approx(ratio * m.Rm, rel=1e-9), \
            f"{m.name}: sigma_D doesn't match {ratio}·Rm"
