from datetime import date
from enum import Enum

from pydantic import BaseModel


class VehicleClass(str, Enum):
    commercial = "commercial"
    passenger = "passenger"
    ev = "ev"


class VehicleStatus(str, Enum):
    active = "active"
    maintenance = "maintenance"
    overdue = "overdue"
    retired = "retired"


class Vehicle(BaseModel):
    id: str
    make: str
    model: str
    year: int
    vehicle_class: VehicleClass
    location: str
    mileage_km: int
    assigned_driver: str | None


class ServiceRecord(BaseModel):
    vehicle_id: str
    service_date: date
    mileage_at_service: int
    work_performed: str
    cost_eur: float


class MaintenanceDetail(BaseModel):
    status: VehicleStatus
    next_service_date: date
    next_service_km: int
    priority: int


class VehicleResponse(BaseModel):
    id: str
    make: str
    model: str
    year: int
    vehicle_class: VehicleClass
    location: str
    mileage_km: int
    assigned_driver: str | None
    status: VehicleStatus
    next_service_date: date
    next_service_km: int
    priority: int
