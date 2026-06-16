import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import data_loader, maintenance
from .models import MaintenanceDetail, VehicleResponse

app = FastAPI(title="FleetOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/vehicles", response_model=list[VehicleResponse])
def list_vehicles():
    today = datetime.date.today()
    result = []
    for v in data_loader.get_all_vehicles():
        records = data_loader.get_service_records(v.id)
        result.append(
            VehicleResponse(
                **v.model_dump(),
                status=maintenance.status(v, records, today),
                next_service_date=maintenance.next_service(v, records, today)[0],
                next_service_km=maintenance.next_service(v, records, today)[1],
                priority=maintenance.priority(v, records, today),
            )
        )
    result.sort(key=lambda r: r.priority, reverse=True)
    return result


@app.get("/vehicles/{vehicle_id}/maintenance", response_model=MaintenanceDetail)
def get_maintenance(vehicle_id: str):
    v = data_loader.get_vehicle(vehicle_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    today = datetime.date.today()
    records = data_loader.get_service_records(v.id)
    due_date, due_km = maintenance.next_service(v, records, today)
    return MaintenanceDetail(
        status=maintenance.status(v, records, today),
        next_service_date=due_date,
        next_service_km=due_km,
        priority=maintenance.priority(v, records, today),
    )
