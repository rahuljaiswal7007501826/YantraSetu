"""Pure helper-function tests (no database)."""
from datetime import time

from app.services.allocation_engine import COMPATIBILITY, compatible_types, is_compatible
from app.services.demand_engine import _risk_level
from app.services.utilization_engine import (
    _safe_div,
    _slot_hours,
    network_efficiency_score,
)
from app.utils.geo import haversine_km


def test_slot_hours():
    assert _slot_hours(time(8, 0), time(18, 0)) == 10.0
    assert _slot_hours(time(9, 30), time(10, 0)) == 0.5
    # Reversed/overnight span clamps to 0 (never negative).
    assert _slot_hours(time(18, 0), time(8, 0)) == 0.0


def test_safe_div():
    assert _safe_div(10, 4) == 2.5
    assert _safe_div(5, 0) == 0.0  # no divide-by-zero
    assert _safe_div(0, 0) == 0.0


def test_network_efficiency_score_formula():
    r = network_efficiency_score(0.5, 0.4, 0.8)
    # 100 * (0.40*0.5 + 0.35*0.4 + 0.25*0.8) = 54.0
    assert r["network_efficiency_score"] == 54.0
    assert r["components"]["utilization_ratio"] == 0.5
    assert r["components"]["shortage_relief_ratio"] == 0.8


def test_nes_clamped_0_to_100():
    assert network_efficiency_score(0, 0, 0)["network_efficiency_score"] == 0.0
    assert network_efficiency_score(1, 1, 1)["network_efficiency_score"] == 100.0


def test_risk_levels():
    assert _risk_level(0.98, 12) == "CRITICAL"
    assert _risk_level(0.55, 6) == "HIGH"
    assert _risk_level(0.30, 2) == "MEDIUM"
    assert _risk_level(0.10, 1) == "LOW"
    # High probability but tiny volume is not CRITICAL (volume gate).
    assert _risk_level(0.70, 3) == "MEDIUM"


def test_compatibility_hard_gate():
    assert is_compatible("Harvesting", "Combine Harvester") is True
    assert is_compatible("Harvesting", "Tractor") is False
    assert compatible_types("Harvesting") == ["Combine Harvester"]
    assert compatible_types("UnknownOp") == []
    # Every operation maps to at least one machine type.
    assert all(len(v) >= 1 for v in COMPATIBILITY.values())


def test_haversine():
    assert haversine_km(26.5, 80.9, 26.5, 80.9) == 0.0
    d = haversine_km(0, 0, 0, 1)  # ~1 degree of longitude at the equator
    assert 110 < d < 112
