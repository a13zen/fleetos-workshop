from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import maintenance
from .data_loader import load_service_history, load_vehicles
from .models import (
    DepotCapacity,
    FuelLogEntry,
    Incident,
    MaintenanceForecast,
    ServiceRecord,
    VehicleWithForecast,
)

DATA_DIR = Path(__file__).parent / "data"
OPS_DB = DATA_DIR / "fleet_ops.db"
SCHEMA = DATA_DIR / "schema.sql"

app = FastAPI(title="FleetOS API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _ensure_ops_db() -> None:
    if not OPS_DB.exists():
        conn = sqlite3.connect(OPS_DB)
        try:
            conn.executescript(SCHEMA.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()


def _ops_query(sql: str) -> list[dict]:
    conn = sqlite3.connect(OPS_DB)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


_vehicles = {v.id: v for v in load_vehicles()}
_history = load_service_history()


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


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


@app.get("/ops/incidents", response_model=list[Incident])
def ops_incidents() -> list[dict]:
    return _ops_query("SELECT * FROM incidents ORDER BY reported_at DESC")


@app.get("/ops/fuel_log", response_model=list[FuelLogEntry])
def ops_fuel_log() -> list[dict]:
    return _ops_query("SELECT * FROM fuel_log ORDER BY log_date DESC")


@app.get("/ops/depot_capacity", response_model=list[DepotCapacity])
def ops_depot_capacity() -> list[dict]:
    return _ops_query("SELECT * FROM depot_capacity ORDER BY depot")
