"""RDM validation: the 6 mandatory test cases plus validation/verdict checks."""

import math

import pytest
from pydantic import ValidationError

from core.beam import Beam, VerdictThresholds, analyze, verdict
from core.loads import DistributedLoad, PointLoad, SupportType
from core.materials import get_material
from core.sections import CircularSection, RectangularSection


# Helpers --------------------------------------------------------------------

S235 = get_material("S235")


def _ss_beam(L, section, loads):
    return Beam(
        length=L,
        material=S235,
        section=section,
        support=SupportType.SIMPLY_SUPPORTED,
        loads=loads,
    )


def _cantilever(L, section, loads):
    return Beam(
        length=L,
        material=S235,
        section=section,
        support=SupportType.CANTILEVER,
        loads=loads,
    )


# Case 1 — Simply supported + central point load -----------------------------
def test_case1_ss_central_point_load():
    L = 4.0
    P = 10_000.0  # 10 kN
    sec = RectangularSection(width=0.05, height=0.10)
    EI = S235.E * sec.inertia
    beam = _ss_beam(L, sec, [PointLoad(magnitude=P, position=L / 2)])
    r = analyze(beam)

    assert r.M_max == pytest.approx(P * L / 4, rel=1e-9)
    assert r.f_max == pytest.approx(P * L ** 3 / (48 * EI), rel=1e-9)
    assert r.reactions["Ra"] == pytest.approx(P / 2, rel=1e-9)
    assert r.reactions["Rb"] == pytest.approx(P / 2, rel=1e-9)
    assert r.sigma_max == pytest.approx(r.M_max / sec.section_modulus, rel=1e-9)


# Case 2 — Simply supported + uniformly distributed load ---------------------
def test_case2_ss_uniform_distributed():
    L = 3.0
    q = 5_000.0  # 5 kN/m
    sec = RectangularSection(width=0.06, height=0.12)
    EI = S235.E * sec.inertia
    beam = _ss_beam(L, sec, [DistributedLoad(magnitude=q, start=0.0, end=L)])
    r = analyze(beam)

    assert r.M_max == pytest.approx(q * L ** 2 / 8, rel=1e-9)
    assert r.f_max == pytest.approx(5 * q * L ** 4 / (384 * EI), rel=1e-9)
    assert r.reactions["Ra"] == pytest.approx(q * L / 2, rel=1e-9)
    assert r.reactions["Rb"] == pytest.approx(q * L / 2, rel=1e-9)


# Case 3 — Cantilever + point load at free end -------------------------------
def test_case3_cantilever_tip_point_load():
    L = 2.0
    P = 2_000.0
    sec = RectangularSection(width=0.04, height=0.08)
    EI = S235.E * sec.inertia
    beam = _cantilever(L, sec, [PointLoad(magnitude=P, position=L)])
    r = analyze(beam)

    assert r.M_max == pytest.approx(P * L, rel=1e-9)
    assert r.f_max == pytest.approx(P * L ** 3 / (3 * EI), rel=1e-9)
    assert r.reactions["R"] == pytest.approx(P, rel=1e-9)
    assert r.reactions["M_r"] == pytest.approx(P * L, rel=1e-9)


# Case 4 — Cantilever + uniformly distributed load ---------------------------
def test_case4_cantilever_uniform_distributed():
    L = 2.5
    q = 3_000.0
    sec = RectangularSection(width=0.05, height=0.10)
    EI = S235.E * sec.inertia
    beam = _cantilever(L, sec, [DistributedLoad(magnitude=q, start=0.0, end=L)])
    r = analyze(beam)

    assert r.M_max == pytest.approx(q * L ** 2 / 2, rel=1e-9)
    assert r.f_max == pytest.approx(q * L ** 4 / (8 * EI), rel=1e-9)
    assert r.reactions["R"] == pytest.approx(q * L, rel=1e-9)
    assert r.reactions["M_r"] == pytest.approx(q * L * L / 2, rel=1e-9)


# Case 5 — Rectangular section properties ------------------------------------
def test_case5_rectangular_section_properties():
    b, h = 0.05, 0.10
    s = RectangularSection(width=b, height=h)
    assert s.inertia == pytest.approx(b * h ** 3 / 12)
    assert s.section_modulus == pytest.approx(b * h ** 2 / 6)


# Case 6 — Validation: negative magnitude / zero dimension -------------------
def test_case6_negative_load_rejected():
    with pytest.raises(ValidationError):
        PointLoad(magnitude=-100, position=1.0)


def test_case6_zero_section_dimension_rejected():
    with pytest.raises(ValidationError):
        RectangularSection(width=0.0, height=0.1)


def test_case6_unknown_material_rejected():
    with pytest.raises(ValueError):
        get_material("Inconnu")


def test_case6_load_outside_beam_rejected():
    sec = RectangularSection(width=0.05, height=0.1)
    with pytest.raises(ValidationError):
        Beam(
            length=2.0,
            material=S235,
            section=sec,
            support=SupportType.SIMPLY_SUPPORTED,
            loads=[PointLoad(magnitude=1000, position=3.0)],
        )


# Verdict thresholds ---------------------------------------------------------
@pytest.mark.parametrize(
    "cs, expected",
    [
        (0.5, "Sous-dimensionné"),
        (1.0, "Limite"),
        (1.49, "Limite"),
        (1.5, "OK"),
        (3.0, "OK"),
        (4.0, "OK"),
        (4.0001, "Surdimensionné"),
        (10.0, "Surdimensionné"),
    ],
)
def test_verdict_labels(cs, expected):
    assert verdict(cs) == expected


def test_verdict_thresholds_are_overridable():
    t = VerdictThresholds(under=2.0, limit=3.0, over=5.0)
    assert verdict(1.5, t) == "Sous-dimensionné"
    assert verdict(2.5, t) == "Limite"
    assert verdict(4.0, t) == "OK"
    assert verdict(6.0, t) == "Surdimensionné"


# Cs propagation -------------------------------------------------------------
def test_safety_factor_propagation():
    L = 2.0
    sec = RectangularSection(width=0.05, height=0.10)
    beam = _ss_beam(L, sec, [PointLoad(magnitude=5_000, position=L / 2)])
    r = analyze(beam)
    expected_cs = S235.Re / r.sigma_max
    assert r.Cs == pytest.approx(expected_cs, rel=1e-12)


# Section module independence (circular shape) -------------------------------
def test_cantilever_with_circular_section():
    L = 1.0
    P = 1_000.0
    sec = CircularSection(diameter=0.03)
    EI = S235.E * sec.inertia
    beam = _cantilever(L, sec, [PointLoad(magnitude=P, position=L)])
    r = analyze(beam)
    assert r.M_max == pytest.approx(P * L, rel=1e-9)
    assert r.f_max == pytest.approx(P * L ** 3 / (3 * EI), rel=1e-9)


# core/ purity: no FastAPI import --------------------------------------------
def test_core_does_not_import_fastapi():
    """Run in a subprocess so the check is unaffected by API tests sharing
    the same interpreter session.

    The subprocess gets `backend/` as its cwd AND as PYTHONPATH so that
    `import core` resolves regardless of where pytest was launched from
    (project root, backend/, IDE, CI, ...).
    """
    import os
    import subprocess
    import sys
    from pathlib import Path

    # backend/core/tests/test_beam.py → parents[2] = backend/
    backend_dir = Path(__file__).resolve().parents[2]
    assert (backend_dir / "core" / "__init__.py").exists(), (
        f"expected backend layout at {backend_dir}"
    )

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{backend_dir}{os.pathsep}{existing}" if existing else str(backend_dir)
    )

    script = (
        "import core, sys; "
        "leaked = [m for m in sys.modules if m == 'fastapi' or m.startswith('fastapi.')]; "
        "assert not leaked, leaked"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
        cwd=str(backend_dir),
        env=env,
    )
    assert result.returncode == 0, result.stderr
