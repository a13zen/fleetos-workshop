"""Pydantic models for FleetOS API."""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Optional

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
    assigned_driver: str = ""


class ServiceRecord(BaseModel):
    vehicle_id: str
    service_date: datetime.date
    mileage_at_service: int
    work_performed: str = ""
    cost_eur: float = 0.0


class MaintenanceResult(BaseModel):
    vehicle_id: str
    status: VehicleStatus
    next_service_date: datetime.date
    next_service_km: int
    priority: int
    last_service_date: Optional[datetime.date] = None


class VehicleWithMaintenance(BaseModel):
    id: str
    make: str
    model: str
    year: int
    vehicle_class: VehicleClass
    location: str
    mileage_km: int
    assigned_driver: str = ""
    status: VehicleStatus
    next_service_date: datetime.date
    next_service_km: int
    priority: int
    last_service_date: Optional[datetime.date] = None
