from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel


class VehicleClass(str, Enum):
    COMMERCIAL = "commercial"
    PASSENGER = "passenger"
    EV = "ev"


class VehicleStatus(str, Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    OVERDUE = "overdue"
    RETIRED = "retired"


class ServiceRecord(BaseModel):
    vehicle_id: str
    service_date: date
    mileage_at_service: int
    work_performed: str
    cost_eur: float


class Vehicle(BaseModel):
    id: str
    make: str
    model: str
    year: int
    vehicle_class: VehicleClass
    location: str
    mileage_km: int
    assigned_driver: str | None = None


class MaintenanceForecast(BaseModel):
    vehicle_id: str
    status: VehicleStatus
    last_service_date: date | None
    next_service_date: date
    next_service_km: int
    priority: int


class VehicleWithForecast(Vehicle):
    status: VehicleStatus
    last_service_date: date | None
    next_service_date: date
    priority: int
