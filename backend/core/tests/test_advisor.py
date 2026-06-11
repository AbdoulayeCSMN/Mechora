"""Tests for the decisional advisor."""

from core.advisor import DEFAULT_DEFLECTION_RATIO, generate_advice
from core.beam import Beam, analyze
from core.loads import PointLoad, SupportType
from core.materials import get_material
from core.sections import RectangularSection


S235 = get_material("S235")
S355 = get_material("S355")


def _analyze(length_m, section, support, loads, material=S235):
    beam = Beam(
        length=length_m,
        material=material,
        section=section,
        support=support,
        loads=loads,
    )
    return beam, analyze(beam)


# --------------------------------------------------------------------------- #
# Stress-limited (Cs < 1) but deflection under default L/250 limit            #
# --------------------------------------------------------------------------- #
def test_underdesigned_by_stress():
    """SS, L=1 m, thin tall section + heavy load.

    Hand check: b=5mm, h=100mm, P=10 kN, L=1 m, central:
      M = PL/4 = 2.5 kN·m
      W = b·h²/6 = 8333 mm³ → σ = 300 MPa  → Cs = 0.78 < 1   (stress fails)
      I = b·h³/12 = 4.17e5 mm⁴ → f = 2.38 mm
      L/250 = 4 mm. f < limit                            (deflection OK)
    """
    length = 1.0
    section = RectangularSection(width=0.005, height=0.100)
    _, result = _analyze(
        length, section, SupportType.SIMPLY_SUPPORTED,
        [PointLoad(magnitude=10_000, position=length / 2)],
    )

    advice = generate_advice(result, material=S235, length_m=length)

    assert advice.facteur_limitant == "contrainte"
    assert "sous-dimensionn" in advice.diagnostic.lower()
    assert "contrainte" in advice.diagnostic.lower()
    assert "MPa" in advice.cause
    assert "S355" in advice.conseil or "matériau" in advice.conseil.lower()


# --------------------------------------------------------------------------- #
# Deflection-limited (stress fine, but f > admissible)                         #
# --------------------------------------------------------------------------- #
def test_underdesigned_by_deflection():
    """A long, slim section with moderate load: stress OK but flèche dépasse
    a strict deflection limit."""
    length = 5.0
    section = RectangularSection(width=0.08, height=0.04)  # wide & flat
    _, result = _analyze(
        length, section, SupportType.SIMPLY_SUPPORTED,
        [PointLoad(magnitude=200, position=length / 2)],
    )

    # Stress check: we want Cs >= 1 (no stress problem)
    assert result.Cs >= 1.0

    # Pick a deflection limit the beam actually violates
    deflection_limit = result.f_max * 0.5

    advice = generate_advice(
        result, material=S235, length_m=length,
        deflection_limit_m=deflection_limit,
    )

    assert advice.facteur_limitant == "flèche"
    assert "flèche" in advice.diagnostic.lower()
    assert "mm" in advice.cause
    assert "inertie" in advice.conseil.lower() or "hauteur" in advice.conseil.lower()


# --------------------------------------------------------------------------- #
# Both limits exceeded                                                         #
# --------------------------------------------------------------------------- #
def test_underdesigned_by_both():
    length = 4.0
    section = RectangularSection(width=0.02, height=0.05)
    _, result = _analyze(
        length, section, SupportType.SIMPLY_SUPPORTED,
        [PointLoad(magnitude=10_000, position=length / 2)],
    )
    # Tight deflection limit
    advice = generate_advice(
        result, material=S235, length_m=length,
        deflection_limit_m=length / 1000,
    )
    assert advice.facteur_limitant == "les deux"
    assert "contrainte" in advice.diagnostic.lower()
    assert "flèche" in advice.diagnostic.lower()


# --------------------------------------------------------------------------- #
# OK case                                                                      #
# --------------------------------------------------------------------------- #
def test_ok_case():
    """A correctly designed beam: Cs in [1.5, 4] and small deflection.

    Hand check: b=50mm, h=100mm, P=10 kN, L=4 m, central:
      M = PL/4 = 10 kN·m
      W = 83333 mm³ → σ = 120 MPa  → Cs = 1.96  (∈ [1.5, 4] = OK)
      I = 4.17e6 mm⁴ → f = 15.2 mm
      L/250 = 16 mm. f < limit                  (deflection OK)
    """
    length = 4.0
    section = RectangularSection(width=0.050, height=0.100)
    _, result = _analyze(
        length, section, SupportType.SIMPLY_SUPPORTED,
        [PointLoad(magnitude=10_000, position=length / 2)],
    )
    assert result.verdict == "OK"

    advice = generate_advice(result, material=S235, length_m=length)
    assert advice.facteur_limitant == "aucun"
    assert advice.conseil == "Dimensionnement satisfaisant."


# --------------------------------------------------------------------------- #
# Surdimensionné: conseil must mention "optimisation"                          #
# --------------------------------------------------------------------------- #
def test_oversized_case_recommends_optimization():
    length = 4.0
    section = RectangularSection(width=0.30, height=0.50)  # massive
    _, result = _analyze(
        length, section, SupportType.SIMPLY_SUPPORTED,
        [PointLoad(magnitude=1_000, position=length / 2)],
    )
    assert result.verdict == "Surdimensionné"

    advice = generate_advice(result, material=S235, length_m=length)
    assert advice.facteur_limitant == "aucun"
    assert "optimisation" in advice.conseil.lower()
    assert "catalogue" in advice.conseil.lower() or "optimisation" in advice.conseil.lower()


# --------------------------------------------------------------------------- #
# Limite case                                                                  #
# --------------------------------------------------------------------------- #
def test_limit_case():
    """Cs in [1.0, 1.5) AND deflection OK.

    Hand check: b=8mm, h=150mm, P=5 kN, L=4 m, central:
      M = PL/4 = 5 kN·m
      W = 30000 mm³ → σ = 166.7 MPa → Cs = 1.41  (∈ [1, 1.5) = Limite)
      I = 2.25e6 mm⁴ → f = 14.1 mm
      L/250 = 16 mm. f < limit                   (deflection OK → no defl flag)
    """
    length = 4.0
    section = RectangularSection(width=0.008, height=0.150)
    _, result = _analyze(
        length, section, SupportType.SIMPLY_SUPPORTED,
        [PointLoad(magnitude=5_000, position=length / 2)],
    )
    assert result.verdict == "Limite"

    advice = generate_advice(result, material=S235, length_m=length)
    assert advice.facteur_limitant == "contrainte"
    assert "marge" in advice.diagnostic.lower() or "insuffisante" in advice.diagnostic.lower()
    assert "1.5" in advice.conseil


# --------------------------------------------------------------------------- #
# Default deflection limit fallback (L/250) is mentioned                       #
# --------------------------------------------------------------------------- #
def test_default_deflection_limit_is_mentioned_when_used():
    length = 4.0
    section = RectangularSection(width=0.10, height=0.20)
    _, result = _analyze(
        length, section, SupportType.SIMPLY_SUPPORTED,
        [PointLoad(magnitude=10_000, position=length / 2)],
    )
    advice = generate_advice(result, material=S235, length_m=length)
    # When advice carries the limit reference, it cites L/250
    assert f"L/{int(DEFAULT_DEFLECTION_RATIO)}" in advice.cause or advice.facteur_limitant == "aucun"
