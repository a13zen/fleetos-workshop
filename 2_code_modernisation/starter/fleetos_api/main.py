"""FleetOS FastAPI application.

Endpoints:
  GET /vehicles                    - all vehicles with status and maintenance info
  GET /vehicles/{id}/maintenance   - maintenance details for one vehicle

Runs on port 8001. CORS enabled for localhost:8000.
"""
from __future__ import annotations

import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fleetos_api.data_loader import load_vehicles, load_service_history
from fleetos_api.maintenance import calc_next_service, calc_status, calc_priority
from fleetos_api.models import VehicleWithMaintenance, MaintenanceResult

app = FastAPI(title="FleetOS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/vehicles", response_model=List[VehicleWithMaintenance])
def get_vehicles():
    """Return all vehicles with their current status and maintenance info."""
    today = datetime.date.today()
    vehicles = load_vehicles()
    service_history = load_service_history()

    # Build a lookup for last service date per vehicle
    from fleetos_api.maintenance import _last_service

    results: List[VehicleWithMaintenance] = []
    for v in vehicles:
        due_date, due_km = calc_next_service(v, service_history, today)
        status = calc_status(v, service_history, today)
        priority = calc_priority(v, service_history, today)
        last = _last_service(v.id, service_history)
        results.append(
            VehicleWithMaintenance(
                id=v.id,
                make=v.make,
                model=v.model,
                year=v.year,
                vehicle_class=v.vehicle_class,
                location=v.location,
                mileage_km=v.mileage_km,
                assigned_driver=v.assigned_driver,
                status=status,
                next_service_date=due_date,
                next_service_km=due_km,
                priority=priority,
                last_service_date=last.service_date if last else None,
            )
        )
    return results


@app.get("/vehicles/{vehicle_id}/maintenance", response_model=MaintenanceResult)
def get_vehicle_maintenance(vehicle_id: str):
    """Return maintenance details for a single vehicle."""
    today = datetime.date.today()
    vehicles = load_vehicles()
    vehicle = next((v for v in vehicles if v.id == vehicle_id), None)
    if vehicle is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id!r} not found")

    service_history = load_service_history()
    from fleetos_api.maintenance import _last_service

    due_date, due_km = calc_next_service(vehicle, service_history, today)
    status = calc_status(vehicle, service_history, today)
    priority = calc_priority(vehicle, service_history, today)
    last = _last_service(vehicle.id, service_history)

    return MaintenanceResult(
        vehicle_id=vehicle.id,
        status=status,
        next_service_date=due_date,
        next_service_km=due_km,
        priority=priority,
        last_service_date=last.service_date if last else None,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fleetos_api.main:app", host="0.0.0.0", port=8001, reload=False)
