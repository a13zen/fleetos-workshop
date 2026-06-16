"""Maintenance scheduling rules extracted from legacy FleetTracker.

These functions are pure: they take domain objects and a reference date, and
return a forecast. No I/O, no globals, no Flask — so they can be unit-tested
and reused by any caller (API, batch job, agent).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import (
    MaintenanceForecast,
    ServiceRecord,
    Vehicle,
    VehicleClass,
    VehicleStatus,
)

RETIRE_KM = 220_000
OVERDUE_GRACE_DAYS = 14
RECENTLY_SERVICED_DAYS = 3


@dataclass(frozen=True)
class ServiceInterval:
    km: int
    months: int


INTERVALS: dict[VehicleClass, ServiceInterval] = {
    VehicleClass.COMMERCIAL: ServiceInterval(km=30_000, months=6),
    VehicleClass.PASSENGER: ServiceInterval(km=20_000, months=6),
    VehicleClass.EV: ServiceInterval(km=40_000, months=12),
}


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, [31, 29 if _is_leap(y) else 28, 31, 30, 31, 30,
                      31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def last_service(history: list[ServiceRecord]) -> ServiceRecord | None:
    if not history:
        return None
    return max(history, key=lambda r: r.service_date)


def next_service_due(
    vehicle: Vehicle, history: list[ServiceRecord], today: date
) -> tuple[date, int]:
    """Return (due_date, due_km) — whichever threshold is hit first triggers service."""
    last = last_service(history)
    interval = INTERVALS[vehicle.vehicle_class]
    if last is None:
        return today, vehicle.mileage_km
    return _add_months(last.service_date, interval.months), last.mileage_at_service + interval.km


def compute_status(
    vehicle: Vehicle, history: list[ServiceRecord], today: date
) -> VehicleStatus:
    if vehicle.mileage_km >= RETIRE_KM:
        return VehicleStatus.RETIRED

    due_date, due_km = next_service_due(vehicle, history, today)

    if vehicle.mileage_km >= due_km:
        return VehicleStatus.OVERDUE

    if today > due_date:
        days_past = (today - due_date).days
        return VehicleStatus.OVERDUE if days_past > OVERDUE_GRACE_DAYS else VehicleStatus.MAINTENANCE

    last = last_service(history)
    if last and (today - last.service_date).days <= RECENTLY_SERVICED_DAYS:
        return VehicleStatus.MAINTENANCE

    return VehicleStatus.ACTIVE


def compute_priority(
    vehicle: Vehicle, history: list[ServiceRecord], today: date
) -> int:
    """0 = no action needed, 100 = urgent. Weighting per 2018 workshop agreement."""
    if compute_status(vehicle, history, today) == VehicleStatus.RETIRED:
        return 0

    due_date, due_km = next_service_due(vehicle, history, today)
    days_over = max(0, (today - due_date).days)
    km_over = max(0, vehicle.mileage_km - due_km)

    score = min(days_over, 60) + min(km_over // 250, 40)
    if vehicle.vehicle_class == VehicleClass.COMMERCIAL:
        score += 10
    return min(score, 100)


def forecast(
    vehicle: Vehicle, history: list[ServiceRecord], today: date
) -> MaintenanceForecast:
    last = last_service(history)
    due_date, due_km = next_service_due(vehicle, history, today)
    return MaintenanceForecast(
        vehicle_id=vehicle.id,
        status=compute_status(vehicle, history, today),
        last_service_date=last.service_date if last else None,
        next_service_date=due_date,
        next_service_km=due_km,
        priority=compute_priority(vehicle, history, today),
    )
