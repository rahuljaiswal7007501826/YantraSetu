"""Shared pytest fixtures (Phase 9.7).

Every test runs against a fresh in-memory SQLite database - the real project
database is never touched. The `scenario` fixture seeds a small, deterministic
supply/demand imbalance the engines can reason about.
"""
from datetime import date, time, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: F401 - registers all tables on Base.metadata
from app.models import CHC, DemandRequest, Farmer, Field, Machine, MachineAvailability


@pytest.fixture
def session():
    """A fresh, isolated in-memory database session per test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = TestSession()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def scenario(session):
    """Seed a deterministic imbalance:

        North cluster : 1 idle Combine Harvester (surplus, available all week).
        South cluster : 1 booked Tractor + 12 pending Harvesting requests, and
                        NO combine -> a CRITICAL combine shortage.

    This is exactly the situation relocation is meant to solve, so the demand,
    allocation, relocation, utilization and impact engines all have something
    real to compute. Returns the key ids for assertions.
    """
    today = date.today()

    north = CHC(name="North CHC", location="North", latitude=27.00, longitude=80.00)
    south = CHC(name="South CHC", location="South", latitude=26.60, longitude=80.30)
    session.add_all([north, south])
    session.flush()

    combine = Machine(
        chc_id=north.id, machine_type="Combine Harvester", capacity=4.0,
        operating_radius=100.0, maintenance_status="operational",
        current_latitude=27.00, current_longitude=80.00,
    )
    tractor = Machine(
        chc_id=south.id, machine_type="Tractor", capacity=3.0,
        operating_radius=80.0, maintenance_status="operational",
        current_latitude=26.60, current_longitude=80.30,
    )
    session.add_all([combine, tractor])
    session.flush()

    # 4 days of slots: combine idle/available (candidate), tractor booked (busy).
    for d in range(4):
        day = today + timedelta(days=d)
        session.add(MachineAvailability(
            machine_id=combine.id, date=day,
            start_time=time(8, 0), end_time=time(18, 0), status="available",
        ))
        session.add(MachineAvailability(
            machine_id=tractor.id, date=day,
            start_time=time(8, 0), end_time=time(18, 0), status="booked",
        ))

    # 12 pending Harvesting requests in the South cluster -> combine shortage.
    request_ids = []
    for i in range(12):
        farmer = Farmer(
            name=f"Farmer {i}", phone="0000000000", village="Southville",
            latitude=26.60, longitude=80.30,
        )
        session.add(farmer)
        session.flush()
        fld = Field(
            farmer_id=farmer.id, crop_type="Wheat", area=3.0,
            latitude=26.60 + i * 0.001, longitude=80.30 + i * 0.001,
        )
        session.add(fld)
        session.flush()
        req = DemandRequest(
            farmer_id=farmer.id, field_id=fld.id, operation_type="Harvesting",
            requested_date=today + timedelta(days=2), urgency="high", status="pending",
        )
        session.add(req)
        session.flush()
        request_ids.append(req.id)

    session.commit()
    return {
        "today": today,
        "north_id": north.id,
        "south_id": south.id,
        "combine_id": combine.id,
        "tractor_id": tractor.id,
        "request_ids": request_ids,
    }
