"""End-to-end tests for POST /optimize/beam."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_optimize_finds_intermediate_profile():
    """L=4m, P=10 kN central, S235, target Cs=2, L/200 → IPE 160 expected."""
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 10.0, "position_m": 2.0}],
        "target_safety_factor": 2.0,
        "deflection_ratio": 200.0,
        "catalogs": ["IPE"],
    }
    r = client.post("/optimize/beam", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["found"] is True
    assert data["optimal"]["designation"] == "IPE 160"
    assert data["optimal"]["family"] == "IPE"

    # All 9 IPE profiles must appear in the evaluation list
    designations = [e["designation"] for e in data["evaluations"]]
    assert designations[0] == "IPE 80"  # sorted by mass = sorted by index
    assert len(designations) == 9

    # The optimal's full result is returned
    res = data["result"]
    assert res["Cs"] >= 2.0
    assert res["f_max_mm"] <= data["deflection_limit_mm"] + 1e-9

    # Profiles lighter than the optimum are all flagged as NOT OK
    opt_mass = data["optimal"]["mass_kg_per_m"]
    lighter = [e for e in data["evaluations"] if e["mass_kg_per_m"] < opt_mass]
    assert all(e["status"] != "OK" for e in lighter)

    # Advice block at top level + inside the BeamResponse
    assert set(data["advice"]) == {"diagnostic", "cause", "conseil", "facteur_limitant"}
    assert data["advice"]["facteur_limitant"] in {"contrainte", "flèche", "les deux", "aucun"}
    assert set(res["advice"]) == {"diagnostic", "cause", "conseil", "facteur_limitant"}


def test_optimize_no_solution():
    """Massive 200 kN central load → no IPE in the catalog satisfies Cs."""
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 200.0, "position_m": 2.0}],
        "target_safety_factor": 2.0,
        "deflection_ratio": 200.0,
        "catalogs": ["IPE"],
    }
    r = client.post("/optimize/beam", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["found"] is False
    assert data["optimal"] is None
    assert data["result"] is None
    assert len(data["evaluations"]) == 9
    assert all(e["status"] != "OK" for e in data["evaluations"])

    # A meta-advice still tells the user what to relax
    advice = data["advice"]
    assert "aucun" in advice["diagnostic"].lower()
    assert "L/" in advice["conseil"] or "flèche" in advice["conseil"].lower()


def test_optimize_negative_load_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": -10.0, "position_m": 2.0}],
        "target_safety_factor": 2.0,
        "deflection_ratio": 200.0,
        "catalogs": ["IPE"],
    }
    r = client.post("/optimize/beam", json=payload)
    assert r.status_code == 422


def test_optimize_unknown_material_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "Unobtanium",
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 10.0, "position_m": 2.0}],
        "target_safety_factor": 2.0,
        "deflection_ratio": 200.0,
        "catalogs": ["IPE"],
    }
    r = client.post("/optimize/beam", json=payload)
    assert r.status_code == 422


def test_optimize_unknown_catalog_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 10.0, "position_m": 2.0}],
        "target_safety_factor": 2.0,
        "deflection_ratio": 200.0,
        "catalogs": ["DOES_NOT_EXIST"],
    }
    r = client.post("/optimize/beam", json=payload)
    assert r.status_code == 422


def test_optimize_combined_catalogs_ipe_plus_hea():
    """Multi-family optimisation: evaluations cover both families."""
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 10.0, "position_m": 2.0}],
        "target_safety_factor": 2.0,
        "deflection_ratio": 200.0,
        "catalogs": ["IPE", "HEA"],
    }
    r = client.post("/optimize/beam", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["found"] is True
    families_seen = {e["family"] for e in data["evaluations"]}
    assert "IPE" in families_seen and "HEA" in families_seen
    assert data["result"]["Cs"] >= 2.0
    assert data["result"]["f_max_mm"] <= data["deflection_limit_mm"] + 1e-9


def test_optimize_invalid_target_returns_422():
    payload = {
        "length_m": 4.0,
        "material": "S235",
        "support": "simply_supported",
        "loads": [{"type": "point", "magnitude_kN": 10.0, "position_m": 2.0}],
        "target_safety_factor": -1.0,
        "deflection_ratio": 200.0,
        "catalogs": ["IPE"],
    }
    r = client.post("/optimize/beam", json=payload)
    assert r.status_code == 422
