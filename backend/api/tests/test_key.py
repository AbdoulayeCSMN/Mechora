"""TestClient end-to-end tests for /calculate/key and /optimize/key."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_calculate_key_happy_path():
    payload = {
        "shaft_diameter_mm": 25.0,
        "Mt_Nm": 80.0,
        "material_shaft": "S235",
        "hub_material": "steel",
        "l_total_mm": 40.0,
    }
    r = client.post("/calculate/key", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    # ISO 773: d=25 → b=8, h=7
    assert data["section"]["b_mm"] == pytest.approx(8)
    assert data["section"]["h_mm"] == pytest.approx(7)
    assert data["section"]["l_active_mm"] == pytest.approx(40 - 8)
    assert data["limiting_criterion"] in {"cisaillement", "matage"}
    assert set(data["advice"]) == {"diagnostic", "cause", "conseil", "facteur_limitant"}


def test_calculate_key_alu_hub_limits_bearing():
    """Aluminium hub → matage tends to be the limiting criterion."""
    payload = {
        "shaft_diameter_mm": 25.0,
        "Mt_Nm": 120.0,
        "material_shaft": "S235",
        "hub_material": "aluminum",
        "l_total_mm": 25.0,
    }
    r = client.post("/calculate/key", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["limiting_criterion"] == "matage"
    assert data["Cs_bearing"] < data["Cs_shear"]


def test_calculate_key_d_above_iso_returns_422():
    payload = {
        "shaft_diameter_mm": 100.0,
        "Mt_Nm": 80.0,
        "material_shaft": "S235",
        "hub_material": "steel",
        "l_total_mm": 40.0,
    }
    r = client.post("/calculate/key", json=payload)
    assert r.status_code == 422


def test_calculate_key_zero_mt_returns_422():
    payload = {
        "shaft_diameter_mm": 25.0,
        "Mt_Nm": 0.0,
        "material_shaft": "S235",
        "hub_material": "steel",
        "l_total_mm": 40.0,
    }
    r = client.post("/calculate/key", json=payload)
    assert r.status_code == 422


def test_calculate_key_unknown_material_returns_422():
    payload = {
        "shaft_diameter_mm": 25.0,
        "Mt_Nm": 80.0,
        "material_shaft": "Unobtanium",
        "hub_material": "steel",
        "l_total_mm": 40.0,
    }
    r = client.post("/calculate/key", json=payload)
    assert r.status_code == 422


def test_optimize_key_happy_path():
    payload = {
        "shaft_diameter_mm": 25.0,
        "Mt_Nm": 120.0,
        "material_shaft": "S235",
        "hub_material": "steel",
        "target_cs": 2.0,
        "l_max_mm": 200,
        "step_mm": 1,
    }
    r = client.post("/optimize/key", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["found"] is True
    assert data["result"]["Cs"] >= 2.0


def test_optimize_key_no_solution():
    payload = {
        "shaft_diameter_mm": 12.0,
        "Mt_Nm": 5_000.0,
        "material_shaft": "S235",
        "hub_material": "aluminum",
        "target_cs": 2.0,
        "l_max_mm": 50,
        "step_mm": 1,
    }
    r = client.post("/optimize/key", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["found"] is False
    assert "aucune" in data["advice"]["diagnostic"].lower()
