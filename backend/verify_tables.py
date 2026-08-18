"""
Phase 1, Step 3 - database verification for YantraSetu.

Uses the EXISTING engine / Base / SessionLocal from app.database (no new
connection). It:
  1. Creates the four core tables in PostgreSQL (chcs, machines, farmers, fields).
  2. Asks the live database to confirm those tables really exist.
  3. Inserts one linked set: CHC + Machine, Farmer + Field.
  4. Reads them back in a FRESH session (proves real persistence, not memory).
  5. Verifies the CHC -> Machine and Farmer -> Field relationships.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe verify_tables.py

It is idempotent: re-running first removes its own previous test rows, so you
never get duplicates. (Phase 2's seed step will clear these before loading the
real synthetic demo data.)
"""
import sys

from sqlalchemy import inspect, select

from app.database import Base, SessionLocal, engine
from app.models import CHC, Farmer, Field, Machine

EXPECTED_TABLES = ["chcs", "machines", "farmers", "fields"]

# Distinctive names so we only ever clean up our own verification rows.
CHC_NAME = "Green Valley CHC [verify]"
FARMER_NAME = "Ramesh Kumar [verify]"


def _cleanup(db) -> None:
    """Delete any leftover verification rows. Cascades remove linked machines/fields."""
    for chc in db.scalars(select(CHC).where(CHC.name == CHC_NAME)):
        db.delete(chc)
    for farmer in db.scalars(select(Farmer).where(Farmer.name == FARMER_NAME)):
        db.delete(farmer)
    db.commit()


def main() -> int:
    print(f"Using: {engine.url.render_as_string(hide_password=True)}\n")

    # 1) Create the tables (DDL). create_all only creates what is missing.
    Base.metadata.create_all(bind=engine)

    # 2) Ask PostgreSQL what tables actually exist now.
    actual = set(inspect(engine).get_table_names())
    print("=== Tables created ===")
    for t in EXPECTED_TABLES:
        print(f"  [{'OK' if t in actual else 'MISSING'}] {t}")
    missing = [t for t in EXPECTED_TABLES if t not in actual]
    if missing:
        print(f"[X] These tables are missing: {missing}")
        return 1

    # 3) Insert one linked set of records.
    with SessionLocal() as db:
        _cleanup(db)  # start from a clean slate in case a previous run left rows

        chc = CHC(
            name=CHC_NAME,
            location="Green Valley, District A",
            latitude=26.8467,
            longitude=80.9462,
            operating_hours="08:00-18:00",
        )
        machine = Machine(
            machine_type="Combine Harvester",
            capacity=2.5,
            operating_radius=25.0,
            maintenance_status="operational",
            current_latitude=26.8467,
            current_longitude=80.9462,
            chc=chc,  # link through the relationship; chc_id is filled in for us
        )
        farmer = Farmer(
            name=FARMER_NAME,
            phone="9800000001",
            village="Rampur",
            latitude=26.9000,
            longitude=80.9000,
        )
        field = Field(
            crop_type="Wheat",
            area=4.0,
            latitude=26.9010,
            longitude=80.9010,
            farmer=farmer,  # link through the relationship
        )
        db.add_all([chc, machine, farmer, field])
        db.commit()
        chc_id, machine_id = chc.id, machine.id
        farmer_id, field_id = farmer.id, field.id

    print("\n=== Records inserted ===")
    print(f"  CHC     id={chc_id}  name='{CHC_NAME}'")
    print(f"  Machine id={machine_id}  type='Combine Harvester'  chc_id={chc_id}")
    print(f"  Farmer  id={farmer_id}  name='{FARMER_NAME}'")
    print(f"  Field   id={field_id}  crop='Wheat'  farmer_id={farmer_id}")

    # 4) Read back in a FRESH session, then traverse the relationships.
    with SessionLocal() as db:
        chc = db.get(CHC, chc_id)
        farmer = db.get(Farmer, farmer_id)

        chc_ok = len(chc.machines) == 1 and chc.machines[0].id == machine_id
        rev1_ok = bool(chc.machines) and chc.machines[0].chc.id == chc.id
        farmer_ok = len(farmer.fields) == 1 and farmer.fields[0].id == field_id
        rev2_ok = bool(farmer.fields) and farmer.fields[0].farmer.id == farmer.id

        print("\n=== Relationships verified ===")
        print(f"  CHC '{chc.name}'")
        print(f"    -> machines: {[m.machine_type for m in chc.machines]}   [{'OK' if chc_ok else 'FAIL'}]")
        print(f"    -> Machine back-ref points to this CHC   [{'OK' if rev1_ok else 'FAIL'}]")
        print(f"  Farmer '{farmer.name}'")
        print(f"    -> fields: {[f.crop_type for f in farmer.fields]}   [{'OK' if farmer_ok else 'FAIL'}]")
        print(f"    -> Field back-ref points to this Farmer   [{'OK' if rev2_ok else 'FAIL'}]")

    all_ok = chc_ok and rev1_ok and farmer_ok and rev2_ok
    print("\n=== Test result ===")
    if all_ok:
        print("  SUCCESS - tables exist, records persisted, relationships verified.")
        return 0
    print("  FAILURE - see the FAIL markers above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
