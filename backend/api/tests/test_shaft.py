"""TestClient end-to-end tests for /calculate/shaft and /optimize/shaft."""

import math

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


# --------------------------------------------------------------------------- #
# /calculate/shaft                                                             #
# --------------------------------------------------------------------------- #
def test_calculate_shaft_solid_happy_path():
    d_mm = 40.0
    payload = {
        "type": "solid",
        "d_ext_mm": d_mm,
        "d_int_mm": 0.0,
        "material": "S235",
        "Mf_Nm": 200.0,
        "Mt_Nm": 150.0,
    }
    r = client.post("/calculate/shaft", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    # Cross-check σ_eq formula numerically
    d_m = d_mm * 1e-3
    W_f = math.pi * d_m ** 3 / 32
    W_t = math.pi * d_m ** 3 / 16
    sigma_f = 200.0 / W_f
    tau = 150.0 / W_t
    sigma_eq = math.sqrt(sigma_f ** 2 + 3 * tau ** 2)

    assert data["sigma_f_MPa"] == pytest.approx(sigma_f * 1e-6, rel=1e-9)
    assert data["tau_MPa"] == pytest.approx(tau * 1e-6, rel=1e-9)
    assert data["sigma_eq_MPa"] == pytest.approx(sigma_eq * 1e-6, rel=1e-9)
    assert data["Cs"] == pytest.approx(235e6 / sigma_eq, rel=1e-9)

    # Section props echoed
    sec = data["section"]
    assert sec["type"] == "solid"
    assert sec["d_ext_mm"] == pytest.approx(d_mm)
    assert sec["d_int_mm"] == pytest.approx(0)
    assert sec["W_f_mm3"] == pytest.approx(math.pi * d_mm ** 3 / 32)
    assert sec["W_t_mm3"] == pytest.approx(math.pi * d_mm ** 3 / 16)

    # Advice present and well-formed
    assert set(data["advice"]) == {
        "diagnostic", "cause", "conseil", "facteur_limitant",
    }


def test_calculate_shaft_hollow_happy_path():
    payload = {
        "type": "hollow",
        "d_ext_mm": 60.0,
        "d_int_mm": 40.0,
        "material": "S355",
        "Mf_Nm": 500.0,
        "Mt_Nm": 300.0,
    }
    r = client.post("/calculate/shaft", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    D = 60e-3
    d = 40e-3
    W_f = math.pi * (D ** 4 - d ** 4) / (32 * D)
    sigma_f = 500.0 / W_f
    assert data["sigma_f_MPa"] == pytest.approx(sigma_f * 1e-6, rel=1e-9)
    assert data["section"]["type"] == "hollow"


# --------------------------------------------------------------------------- #
# Validation errors                                                            #
# --------------------------------------------------------------------------- #
def test_calculate_shaft_both_moments_zero_returns_422():
    payload = {
        "type": "solid",
        "d_ext_mm": 40,
        "d_int_mm": 0,
        "material": "S235",
        "Mf_Nm": 0,
        "Mt_Nm": 0,
    }
    r = client.post("/calculate/shaft", json=payload)
    assert r.status_code == 422


def test_calculate_shaft_inner_geq_outer_returns_422():
    payload = {
        "type": "hollow",
        "d_ext_mm": 40,
        "d_int_mm": 40,
        "material": "S235",
        "Mf_Nm": 100,
        "Mt_Nm": 50,
    }
    r = client.post("/calculate/shaft", json=payload)
    assert r.status_code == 422


def test_calculate_shaft_negative_moment_returns_422():
    payload = {
        "type": "solid",
        "d_ext_mm": 40,
        "d_int_mm": 0,
        "material": "S235",
        "Mf_Nm": -10,
        "Mt_Nm": 50,
    }
    r = client.post("/calculate/shaft", json=payload)
    assert r.status_code == 422


def test_calculate_shaft_unknown_material_returns_422():
    payload = {
        "type": "solid",
        "d_ext_mm": 40,
        "d_int_mm": 0,
        "material": "Unobtanium",
        "Mf_Nm": 100,
        "Mt_Nm": 50,
    }
    r = client.post("/calculate/shaft", json=payload)
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# /optimize/shaft                                                              #
# --------------------------------------------------------------------------- #
def test_optimize_shaft_happy_path():
    payload = {
        "type": "solid",
        "material": "S235",
        "Mf_Nm": 200.0,
        "Mt_Nm": 150.0,
        "target_cs": 2.0,
        "d_min_mm": 10,
        "d_max_mm": 80,
        "step_mm": 1,
        "d_int_ratio": 0.7,
    }
    r = client.post("/optimize/shaft", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["found"] is True
    assert data["d_optimal_mm"] is not None
    assert data["result"]["Cs"] >= 2.0


def test_optimize_shaft_no_solution_returns_200():
    payload = {
        "type": "solid",
        "material": "S235",
        "Mf_Nm": 10_000.0,
        "Mt_Nm": 5_000.0,
        "target_cs": 2.0,
        "d_min_mm": 10,
        "d_max_mm": 12,
        "step_mm": 1,
        "d_int_ratio": 0.7,
    }
    r = client.post("/optimize/shaft", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["found"] is False
    assert data["d_optimal_mm"] is None
    assert "aucun" in data["advice"]["diagnostic"].lower()


def test_optimize_shaft_invalid_target_returns_422():
    payload = {
        "type": "solid",
        "material": "S235",
        "Mf_Nm": 100, "Mt_Nm": 50,
        "target_cs": 0,
        "d_min_mm": 10, "d_max_mm": 80, "step_mm": 1, "d_int_ratio": 0.7,
    }
    r = client.post("/optimize/shaft", json=payload)
    assert r.status_code == 422
