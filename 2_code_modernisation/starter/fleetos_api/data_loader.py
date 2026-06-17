"""Data loader — reads legacy CSV files and returns typed models.  No business logic."""
from __future__ import annotations

import csv
import datetime
import os
from typing import List

from fleetos_api.models import Vehicle, ServiceRecord

# CSVs live in legacy_fleettracker/data/ relative to the starter/ root.
_STARTER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_STARTER_DIR, "legacy_fleettracker", "data")


def load_vehicles() -> List[Vehicle]:
    """Load all vehicles from vehicles.csv and return typed Vehicle models."""
    vehicles: List[Vehicle] = []
    path = os.path.join(_DATA_DIR, "vehicles.csv")
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vehicles.append(
                    Vehicle(
                        id=row["id"],
                        make=row["make"],
                        model=row["model"],
                        year=int(row["year"]),
                        vehicle_class=row["vehicle_class"],
                        location=row["location"],
                        mileage_km=int(row["mileage_km"]),
                        assigned_driver=row.get("assigned_driver", "") or "",
                    )
                )
    except FileNotFoundError:
        raise RuntimeError(f"Vehicle data file not found: {path}")
    return vehicles


def load_service_history() -> List[ServiceRecord]:
    """Load all service records from service_history.csv and return typed models."""
    records: List[ServiceRecord] = []
    path = os.path.join(_DATA_DIR, "service_history.csv")
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(
                    ServiceRecord(
                        vehicle_id=row["vehicle_id"],
                        service_date=datetime.date.fromisoformat(row["service_date"]),
                        mileage_at_service=int(row["mileage_at_service"]),
                        work_performed=row.get("work_performed", "") or "",
                        cost_eur=float(row.get("cost_eur", 0) or 0),
                    )
                )
    except FileNotFoundError:
        raise RuntimeError(f"Service history data file not found: {path}")
    return records
