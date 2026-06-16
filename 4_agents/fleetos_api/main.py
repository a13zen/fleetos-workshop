from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import maintenance
from .data_loader import load_service_history, load_vehicles
from .models import MaintenanceForecast, ServiceRecord, VehicleWithForecast

app = FastAPI(title="FleetOS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_vehicles = {v.id: v for v in load_vehicles()}
_history = load_service_history()


@app.get("/vehicles", response_model=list[VehicleWithForecast])
def list_vehicles() -> list[VehicleWithForecast]:
    today = date.today()
    out: list[VehicleWithForecast] = []
    for v in _vehicles.values():
        fc = maintenance.forecast(v, _history.get(v.id, []), today)
        out.append(
            VehicleWithForecast(
                **v.model_dump(),
                status=fc.status,
                last_service_date=fc.last_service_date,
                next_service_date=fc.next_service_date,
                priority=fc.priority,
            )
        )
    out.sort(key=lambda r: r.priority, reverse=True)
    return out


@app.get("/vehicles/{vehicle_id}/maintenance", response_model=MaintenanceForecast)
def vehicle_maintenance(vehicle_id: str) -> MaintenanceForecast:
    v = _vehicles.get(vehicle_id)
    if v is None:
        raise HTTPException(404, "vehicle not found")
    return maintenance.forecast(v, _history.get(vehicle_id, []), date.today())


@app.get("/vehicles/{vehicle_id}/history", response_model=list[ServiceRecord])
def vehicle_history(vehicle_id: str) -> list[ServiceRecord]:
    if vehicle_id not in _vehicles:
        raise HTTPException(404, "vehicle not found")
    return sorted(_history.get(vehicle_id, []), key=lambda r: r.service_date, reverse=True)
