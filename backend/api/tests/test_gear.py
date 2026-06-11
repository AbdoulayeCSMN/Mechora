"""TestClient end-to-end tests for /calculate/gear and /optimize/gear."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_calculate_gear_happy_path():
    payload = {
        "m_mm": 3.0,
        "z1": 20,
        "z2": 40,
        "b_mm": 30.0,
        "Mt1_Nm": 50.0,
        "n1_rpm": 1000.0,
        "material_pinion": "S235",
        "material_gear": "S235",
    }
    r = client.post("/calculate/gear", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["geometry"]["d1_mm"] == pytest.approx(60.0)
    assert data["geometry"]["d2_mm"] == pytest.approx(120.0)
    assert data["geometry"]["u"] == pytest.approx(2.0)
    assert data["limiting_criterion"] in {
        "flexion_pignon", "flexion_roue", "pression_superficielle",
    }
    assert set(data["advice"]) == {"diagnostic", "cause", "conseil", "facteur_limitant"}


def test_calculate_gear_z_below_min_returns_422():
    payload = {
        "m_mm": 3.0,
        "z1": 8,
        "z2": 40,
        "b_mm": 30.0,
        "Mt1_Nm": 50.0,
        "n1_rpm": 1000.0,
        "material_pinion": "S235",
        "material_gear": "S235",
    }
    r = client.post("/calculate/gear", json=payload)
    assert r.status_code == 422


def test_calculate_gear_unknown_material_returns_422():
    payload = {
        "m_mm": 3.0,
        "z1": 20,
        "z2": 40,
        "b_mm": 30.0,
        "Mt1_Nm": 50.0,
        "n1_rpm": 1000.0,
        "material_pinion": "Unobtanium",
        "material_gear": "S235",
    }
    r = client.post("/calculate/gear", json=payload)
    assert r.status_code == 422


def test_calculate_gear_zero_torque_returns_422():
    payload = {
        "m_mm": 3.0,
        "z1": 20,
        "z2": 40,
        "b_mm": 30.0,
        "Mt1_Nm": 0.0,
        "n1_rpm": 1000.0,
        "material_pinion": "S235",
        "material_gear": "S235",
    }
    r = client.post("/calculate/gear", json=payload)
    assert r.status_code == 422


def test_optimize_gear_happy_path():
    payload = {
        "z1": 20,
        "z2": 40,
        "Mt1_Nm": 50.0,
        "n1_rpm": 1000.0,
        "material_pinion": "S235",
        "material_gear": "S235",
        "target_cs": 1.5,
    }
    r = client.post("/optimize/gear", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["found"] is True
    assert data["result"]["Cs"] >= 1.5
    assert data["m_optimal_mm"] is not None


def test_optimize_gear_no_solution():
    payload = {
        "z1": 12,
        "z2": 12,
        "Mt1_Nm": 50_000.0,
        "n1_rpm": 3000.0,
        "material_pinion": "S235",
        "material_gear": "S235",
        "target_cs": 2.0,
    }
    r = client.post("/optimize/gear", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["found"] is False
    assert data["m_optimal_mm"] is None
    assert "aucun" in data["advice"]["diagnostic"].lower()
