import math

import pytest

from core.sections import CircularSection, RectangularSection, TubeSection


def test_rectangle_formulas():
    b, h = 0.05, 0.10  # 50mm x 100mm
    s = RectangularSection(width=b, height=h)
    assert s.area == pytest.approx(b * h)
    assert s.inertia == pytest.approx(b * h ** 3 / 12)
    assert s.extreme_fiber == pytest.approx(h / 2)
    assert s.section_modulus == pytest.approx(b * h ** 2 / 6)


def test_circle_formulas():
    d = 0.04
    s = CircularSection(diameter=d)
    assert s.area == pytest.approx(math.pi * d ** 2 / 4)
    assert s.inertia == pytest.approx(math.pi * d ** 4 / 64)
    assert s.extreme_fiber == pytest.approx(d / 2)
    assert s.section_modulus == pytest.approx(math.pi * d ** 3 / 32)


def test_tube_formulas():
    D, d = 0.06, 0.05
    s = TubeSection(outer_diameter=D, inner_diameter=d)
    assert s.area == pytest.approx(math.pi * (D ** 2 - d ** 2) / 4)
    assert s.inertia == pytest.approx(math.pi * (D ** 4 - d ** 4) / 64)
    assert s.extreme_fiber == pytest.approx(D / 2)


def test_zero_or_negative_dimension_rejected():
    with pytest.raises(Exception):
        RectangularSection(width=0, height=0.1)
    with pytest.raises(Exception):
        RectangularSection(width=0.05, height=-1)
    with pytest.raises(Exception):
        CircularSection(diameter=0)
    with pytest.raises(Exception):
        TubeSection(outer_diameter=0.05, inner_diameter=0.05)
    with pytest.raises(Exception):
        TubeSection(outer_diameter=0.04, inner_diameter=0.05)
