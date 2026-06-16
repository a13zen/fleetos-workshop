import csv
import os
from datetime import date

from .models import ServiceRecord, Vehicle, VehicleClass

DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "starter", "legacy_fleettracker", "data"
)


def _load_csv(name: str) -> list[dict]:
    path = os.path.join(DATA_DIR, name)
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def get_all_vehicles() -> list[Vehicle]:
    return [_parse_vehicle(row) for row in _load_csv("vehicles.csv")]


def get_vehicle(vid: str) -> Vehicle | None:
    for row in _load_csv("vehicles.csv"):
        if row["id"] == vid:
            return _parse_vehicle(row)
    return None


def get_service_records(vid: str) -> list[ServiceRecord]:
    return [
        _parse_service_record(row)
        for row in _load_csv("service_history.csv")
        if row["vehicle_id"] == vid
    ]


def _parse_vehicle(row: dict) -> Vehicle:
    return Vehicle(
        id=row["id"],
        make=row["make"],
        model=row["model"],
        year=int(row["year"]),
        vehicle_class=VehicleClass(row["vehicle_class"]),
        location=row["location"],
        mileage_km=int(row["mileage_km"]),
        assigned_driver=row["assigned_driver"] or None,
    )


def _parse_service_record(row: dict) -> ServiceRecord:
    return ServiceRecord(
        vehicle_id=row["vehicle_id"],
        service_date=date.fromisoformat(row["service_date"]),
        mileage_at_service=int(row["mileage_at_service"]),
        work_performed=row["work_performed"],
        cost_eur=float(row["cost_eur"]),
    )
