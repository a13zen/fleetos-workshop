from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .models import ServiceRecord, Vehicle

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_vehicles() -> list[Vehicle]:
    with (DATA_DIR / "vehicles.csv").open() as f:
        return [
            Vehicle(
                id=r["id"],
                make=r["make"],
                model=r["model"],
                year=int(r["year"]),
                vehicle_class=r["vehicle_class"],
                location=r["location"],
                mileage_km=int(r["mileage_km"]),
                assigned_driver=r["assigned_driver"] or None,
            )
            for r in csv.DictReader(f)
        ]


def load_service_history() -> dict[str, list[ServiceRecord]]:
    by_vehicle: dict[str, list[ServiceRecord]] = defaultdict(list)
    with (DATA_DIR / "service_history.csv").open() as f:
        for r in csv.DictReader(f):
            rec = ServiceRecord(
                vehicle_id=r["vehicle_id"],
                service_date=r["service_date"],
                mileage_at_service=int(r["mileage_at_service"]),
                work_performed=r["work_performed"],
                cost_eur=float(r["cost_eur"]),
            )
            by_vehicle[rec.vehicle_id].append(rec)
    return by_vehicle
