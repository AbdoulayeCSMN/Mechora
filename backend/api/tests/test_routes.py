"""End-to-end tests for POST /calculate/beam via FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.materials import get_material


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# --------------------------------------------------------------------------- #
# Happy path: SS + central point load, matches PL/4 and PL^3/(48EI)            #
# --------------------------------------------------------------------------- #
def test_ss_central_point_load_happy_path():
    L_m = 4.0
    P_kN = 10.0
    b_mm, h_mm = 50.0, 100.0

    payload = {
        "length_m": L_m,
        "material": "S235",
        "section": {"type": "rectangular", "width_mm": b_mm, "height_mm": h_mm},
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": P_kN, "position_m": L_m / 2}],
    }

    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    # M_max = PL/4, in kN*m
    assert data["M_max_kNm"] == pytest.approx(P_kN * L_m / 4, rel=1e-9)

    # f_max = P L^3 / (48 EI), in mm
    P_N = P_kN * 1e3
    b_m, h_m = b_mm * 1e-3, h_mm * 1e-3
    I = b_m * h_m ** 3 / 12
    E = get_material("S235").E
    f_expected_mm = (P_N * L_m ** 3 / (48 * E * I)) * 1e3
    assert data["f_max_mm"] == pytest.approx(f_expected_mm, rel=1e-9)

    # Section properties echoed in mm units
    assert data["section_properties"]["inertia_mm4"] == pytest.approx(b_mm * h_mm ** 3 / 12, rel=1e-9)
    assert data["section_properties"]["section_modulus_mm3"] == pytest.approx(b_mm * h_mm ** 2 / 6, rel=1e-9)

    # Reactions = P/2 each
    assert data["reactions_kN"]["Ra"] == pytest.approx(P_kN / 2, rel=1e-9)
    assert data["reactions_kN"]["Rb"] == pytest.approx(P_kN / 2, rel=1e-9)

    # Arrays consistent
    assert len(data["x_m"]) == len(data["V_kN"]) == len(data["M_kNm"])
    assert data["verdict"] in {"Sous-dimensionné", "Limite", "OK", "Surdimensionné"}

    # Advice block enriches the response
    advice = data["advice"]
    assert set(advice) == {"diagnostic", "cause", "conseil", "facteur_limitant"}
    assert advice["facteur_limitant"] in {"contrainte", "flèche", "les deux", "aucun"}
    assert advice["diagnostic"] and advice["cause"] and advice["conseil"]


def test_advice_present_for_underdesigned_case():
    """A thin section overloaded → 422? No: the calc succeeds but advice flags it."""
    payload = {
        "length_m": 1.0,
        "material": "S235",
        "section": {"type": "rectangular", "width_mm": 5.0, "height_mm": 100.0},
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 10.0, "position_m": 0.5}],
    }
    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["verdict"] == "Sous-dimensionné"
    assert data["advice"]["facteur_limitant"] == "contrainte"
    assert "contrainte" in data["advice"]["diagnostic"].lower()
    # The conseil should point at increasing W or upgrading material
    assert (
        "matériau" in data["advice"]["conseil"].lower()
        or "section" in data["advice"]["conseil"].lower()
    )


# --------------------------------------------------------------------------- #
# Cantilever + UDL, matches qL^2/2 and qL^4/(8EI)                              #
# --------------------------------------------------------------------------- #
def test_cantilever_udl_happy_path():
    L_m = 2.0
    q_kN_per_m = 4.0
    payload = {
        "length_m": L_m,
        "material": "S355",
        "section": {"type": "circular", "diameter_mm": 40.0},
        "support": "cantilever",
        "loads": [{"type": "distributed", "magnitude_kN_per_m": q_kN_per_m,
                   "start_m": 0.0, "end_m": L_m}],
    }
    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["M_max_kNm"] == pytest.approx(q_kN_per_m * L_m ** 2 / 2, rel=1e-9)


# --------------------------------------------------------------------------- #
# Validation errors → 422                                                      #
# --------------------------------------------------------------------------- #
def test_negative_point_load_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "section": {"type": "rectangular", "width_mm": 50.0, "height_mm": 100.0},
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": -5.0, "position_m": 2.0}],
    }
    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 422


def test_zero_section_dimension_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "section": {"type": "rectangular", "width_mm": 0.0, "height_mm": 100.0},
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 5.0, "position_m": 2.0}],
    }
    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 422


def test_unknown_material_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "Unobtanium",
        "section": {"type": "rectangular", "width_mm": 50.0, "height_mm": 100.0},
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 5.0, "position_m": 2.0}],
    }
    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 422
    assert "Unobtanium" in r.text


def test_load_outside_beam_returns_422():
    payload = {
        "length_m": 2.0,
        "material": "S235",
        "section": {"type": "rectangular", "width_mm": 50.0, "height_mm": 100.0},
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 5.0, "position_m": 3.0}],
    }
    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 422


def test_unknown_support_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "section": {"type": "rectangular", "width_mm": 50.0, "height_mm": 100.0},
        "support": "fixed_fixed",  # not in the Literal
        "loads": [{"type": "point", "magnitude_kN": 5.0, "position_m": 2.0}],
    }
    r = client.post("/calculate/beam", json=payload)
    assert r.status_code == 422
