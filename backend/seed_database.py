"""
seed_database.py - generate a realistic SYNTHETIC demo dataset for YantraSetu.

*** Every row created here is SYNTHETIC DEMO DATA (not real people or CHCs). ***

The dataset deliberately contains a supply/demand IMBALANCE so the later phases
have a real problem to solve:

  - Cluster A "Green Valley": combine harvesters sitting mostly IDLE.
  - Cluster B "Riverside / Lakeside": NO local combine harvester, but a pile of
    PENDING harvesting requests  ->  a shortage.
  - Cluster C "Sunrise / Meadow": a couple of combines, partly used.

Later, the relocation engine should recommend moving an idle combine from A (or
C) to cluster B. This script just plants that situation.

Run from the backend/ folder:
    .venv\\Scripts\\python.exe seed_database.py

Safe to re-run: it clears the six tables first, then reseeds. A fixed random
seed keeps the demo reproducible for the SIH presentation.
"""
import random
from datetime import date, time, timedelta

from sqlalchemy import delete, func, select

from app.database import Base, SessionLocal, engine
from app.models import CHC, DemandRequest, Farmer, Field, Machine, MachineAvailability

RANDOM_SEED = 42
DAYS_AHEAD = 7
WORK_START, WORK_END = time(8, 0), time(18, 0)

# Geographic cluster centres (roughly around Uttar Pradesh, India): (lat, lon).
CLUSTERS = {
    "A": (27.10, 80.85),
    "B": (26.50, 80.95),
    "C": (26.85, 81.25),
    "D": (26.80, 80.50),
}

# name, cluster, #combine_harvesters, #tractors, #other_machines
CHC_DEFS = [
    ("Green Valley CHC", "A", 3, 2, 3),   # <- idle combines live here
    ("Hilltop CHC",      "A", 0, 3, 2),
    ("Riverside CHC",    "B", 0, 3, 3),   # <- cluster B: NO combines, big demand
    ("Lakeside CHC",     "B", 0, 2, 2),
    ("Sunrise CHC",      "C", 2, 2, 2),
    ("Meadow CHC",       "C", 1, 2, 2),
    ("Sundar CHC",       "D", 1, 3, 3),
    ("Central CHC",      "D", 1, 2, 2),
]

OTHER_TYPES = ["Rotavator", "Seed Drill", "Sprayer", "Baler", "Laser Land Leveler"]
FIRST_NAMES = ["Ramesh", "Suresh", "Mahesh", "Rajesh", "Anil", "Sunil", "Vijay",
               "Amit", "Ravi", "Deepak", "Manoj", "Sanjay", "Arun", "Prakash",
               "Dinesh", "Rakesh", "Ashok", "Vinod", "Naresh", "Gopal", "Lakshmi",
               "Sita", "Radha", "Anita", "Sunita", "Kavita", "Meena", "Pooja"]
LAST_NAMES = ["Kumar", "Singh", "Yadav", "Verma", "Sharma", "Gupta", "Patel",
              "Pandey", "Mishra", "Tiwari", "Chauhan", "Jha", "Dubey", "Saxena"]
VILLAGES = ["Rampur", "Shyampur", "Govindpur", "Madhavpur", "Krishnanagar",
            "Bhagatpur", "Sultanpur", "Fatehpur", "Raniganj", "Lakshmipur",
            "Haripur", "Devipur", "Narayanpur", "Gopalganj", "Bishnupur"]
HARVEST_CROPS = ["Wheat", "Rice", "Barley"]      # these need a combine harvester
OTHER_CROPS = ["Sugarcane", "Cotton", "Maize", "Mustard", "Potato"]
OTHER_OPS = ["Ploughing", "Sowing", "Spraying", "Tillage"]

# Concentrate demand (farmers) in cluster B so the shortage is realistic.
FARMERS_PER_CLUSTER = {"A": 30, "B": 60, "C": 30, "D": 30}  # 150 total


def jitter(value: float, spread: float = 0.15) -> float:
    """Scatter a point around a centre so things aren't stacked on one pixel."""
    return round(value + random.uniform(-spread, spread), 6)


def clear_all(db) -> None:
    """Delete rows child-first so foreign keys never block the reset."""
    for model in (DemandRequest, MachineAvailability, Machine, Field, Farmer, CHC):
        db.execute(delete(model))
    db.commit()


def seed_chcs(db) -> dict:
    chcs = {}
    for name, cluster, n_comb, n_tract, n_other in CHC_DEFS:
        clat, clon = CLUSTERS[cluster]
        chc = CHC(
            name=f"{name} [demo]",
            location=f"Cluster {cluster}",
            latitude=jitter(clat, 0.05),
            longitude=jitter(clon, 0.05),
            operating_hours="08:00-18:00",
        )
        db.add(chc)
        chcs[name] = (chc, cluster, n_comb, n_tract, n_other)
    db.flush()  # assign chc ids
    return chcs


def seed_machines(db, chcs) -> list:
    machines = []
    for name, (chc, cluster, n_comb, n_tract, n_other) in chcs.items():
        specs = (["Combine Harvester"] * n_comb
                 + ["Tractor"] * n_tract
                 + [random.choice(OTHER_TYPES) for _ in range(n_other)])
        for mtype in specs:
            m = Machine(
                chc_id=chc.id,
                machine_type=mtype,
                capacity=round(random.uniform(1.5, 4.0), 1),
                operating_radius=random.choice([15, 20, 25, 30]),
                maintenance_status="operational",
                current_latitude=jitter(chc.latitude, 0.02),
                current_longitude=jitter(chc.longitude, 0.02),
            )
            db.add(m)
            machines.append((m, cluster, name))
    db.flush()
    # A couple of non-combine machines are under maintenance (realism).
    non_combines = [m for (m, _, _) in machines if m.machine_type != "Combine Harvester"]
    for m in random.sample(non_combines, k=min(2, len(non_combines))):
        m.maintenance_status = "maintenance"
    return machines


def seed_farmers_and_fields(db):
    farmers_by_cluster = {c: [] for c in CLUSTERS}
    fields_by_cluster = {c: [] for c in CLUSTERS}

    for cluster, count in FARMERS_PER_CLUSTER.items():
        clat, clon = CLUSTERS[cluster]
        for _ in range(count):
            farmer = Farmer(
                name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                phone=f"9{random.randint(100000000, 999999999)}",
                village=random.choice(VILLAGES),
                latitude=jitter(clat, 0.20),
                longitude=jitter(clon, 0.20),
            )
            db.add(farmer)
            farmers_by_cluster[cluster].append(farmer)
    db.flush()  # farmer ids

    for cluster, farmers in farmers_by_cluster.items():
        for farmer in farmers:
            for _ in range(random.randint(1, 2)):
                # Cluster B leans toward harvest crops so the demand is for combines.
                if cluster == "B":
                    crop = random.choice(HARVEST_CROPS) if random.random() < 0.7 \
                        else random.choice(OTHER_CROPS)
                else:
                    crop = random.choice(HARVEST_CROPS + OTHER_CROPS)
                field = Field(
                    farmer_id=farmer.id,
                    crop_type=crop,
                    area=round(random.uniform(1.0, 8.0), 1),
                    latitude=jitter(farmer.latitude, 0.03),
                    longitude=jitter(farmer.longitude, 0.03),
                )
                db.add(field)
                fields_by_cluster[cluster].append(field)
    db.flush()  # field ids
    return farmers_by_cluster, fields_by_cluster


def seed_availability(db, machines) -> None:
    today = date.today()
    for m, _cluster, chc_name in machines:
        if m.maintenance_status == "maintenance":
            busy = None  # every slot is "maintenance"
        elif m.machine_type == "Combine Harvester" and chc_name.startswith("Green Valley"):
            busy = 0.05  # our deliberately idle star combines
        elif m.machine_type == "Combine Harvester":
            busy = random.uniform(0.45, 0.80)
        elif m.machine_type == "Tractor":
            busy = random.uniform(0.40, 0.70)
        else:
            busy = random.uniform(0.20, 0.50)

        for d in range(DAYS_AHEAD):
            if busy is None:
                status = "maintenance"
            else:
                status = "booked" if random.random() < busy else "available"
            db.add(MachineAvailability(
                machine_id=m.id,
                date=today + timedelta(days=d),
                start_time=WORK_START,
                end_time=WORK_END,
                status=status,
            ))


def seed_requests(db, fields_by_cluster) -> dict:
    today = date.today()
    tally = {"pending_harvest_B": 0, "historical": 0, "other": 0}

    b_harvest_fields = [f for f in fields_by_cluster["B"] if f.crop_type in HARVEST_CROPS]
    random.shuffle(b_harvest_fields)

    # 1) THE SHORTAGE: ~25 pending harvesting requests in cluster B (needs a combine).
    for field in b_harvest_fields[:25]:
        db.add(DemandRequest(
            farmer_id=field.farmer_id, field_id=field.id,
            operation_type="Harvesting",
            requested_date=today + timedelta(days=random.randint(1, 5)),
            urgency=random.choice(["high", "high", "medium"]),
            status="pending",
        ))
        tally["pending_harvest_B"] += 1

    # 2) Historical completed harvests in B (past 2 weeks) -> demand history for Phase 3.
    for field in b_harvest_fields[:20]:
        db.add(DemandRequest(
            farmer_id=field.farmer_id, field_id=field.id,
            operation_type="Harvesting",
            requested_date=today - timedelta(days=random.randint(1, 14)),
            urgency="medium",
            status="completed",
        ))
        tally["historical"] += 1

    # 3) Assorted requests elsewhere (mixed operations + statuses) for realism.
    other_fields = fields_by_cluster["A"] + fields_by_cluster["C"] + fields_by_cluster["D"]
    for field in random.sample(other_fields, k=min(30, len(other_fields))):
        db.add(DemandRequest(
            farmer_id=field.farmer_id, field_id=field.id,
            operation_type=random.choice(OTHER_OPS),
            requested_date=today + timedelta(days=random.randint(1, 6)),
            urgency=random.choice(["low", "medium", "high"]),
            status=random.choice(["pending", "pending", "completed"]),
        ))
        tally["other"] += 1

    return tally


def print_summary(db, tally) -> None:
    def count(model):
        return db.scalar(select(func.count()).select_from(model))

    print("\n=== YantraSetu demo data (SYNTHETIC) ===")
    print(f"  CHCs:               {count(CHC)}")
    print(f"  Machines:           {count(Machine)}")
    print(f"  Farmers:            {count(Farmer)}")
    print(f"  Fields:             {count(Field)}")
    print(f"  Availability slots: {count(MachineAvailability)}")
    print(f"  Demand requests:    {count(DemandRequest)}")

    print("\n  Combine harvesters per CHC:")
    rows = db.execute(
        select(CHC.name, func.count(Machine.id))
        .join(Machine, Machine.chc_id == CHC.id)
        .where(Machine.machine_type == "Combine Harvester")
        .group_by(CHC.name).order_by(CHC.name)
    ).all()
    for name, n in rows:
        print(f"    {name}: {n}")

    gv = db.scalar(select(CHC).where(CHC.name == "Green Valley CHC [demo]"))
    slot_rows = db.execute(
        select(MachineAvailability.status, func.count())
        .join(Machine, Machine.id == MachineAvailability.machine_id)
        .where(Machine.chc_id == gv.id, Machine.machine_type == "Combine Harvester")
        .group_by(MachineAvailability.status)
    ).all()
    slot_map = {s: c for s, c in slot_rows}
    total = sum(slot_map.values()) or 1
    idle_pct = 100 * slot_map.get("available", 0) / total

    b_combines = db.scalar(
        select(func.count(Machine.id)).join(CHC, CHC.id == Machine.chc_id)
        .where(CHC.name.in_(["Riverside CHC [demo]", "Lakeside CHC [demo]"]),
               Machine.machine_type == "Combine Harvester")
    )
    pending_harvest = db.scalar(
        select(func.count(DemandRequest.id))
        .where(DemandRequest.operation_type == "Harvesting",
               DemandRequest.status == "pending")
    )

    print("\n  >>> INTENTIONAL IMBALANCE <<<")
    print(f"    Green Valley (Cluster A) combines idle: {idle_pct:.0f}% of slots available")
    print(f"    Cluster B (Riverside + Lakeside) combine harvesters: {b_combines}")
    print(f"    Pending 'Harvesting' requests (mostly Cluster B): {pending_harvest}")
    print("    -> later, relocating an idle combine A/C -> B should be recommended.\n")


def main() -> None:
    random.seed(RANDOM_SEED)
    Base.metadata.create_all(bind=engine)  # make sure tables exist
    with SessionLocal() as db:
        clear_all(db)
        chcs = seed_chcs(db)
        machines = seed_machines(db, chcs)
        _, fields_by_cluster = seed_farmers_and_fields(db)
        seed_availability(db, machines)
        tally = seed_requests(db, fields_by_cluster)
        db.commit()
        print_summary(db, tally)
    print("Seeding complete. (All data is synthetic demo data.)")


if __name__ == "__main__":
    main()
