import datetime
from datetime import date

from .models import ServiceRecord, Vehicle, VehicleClass, VehicleStatus

# Identical to legacy constants — do not change without workshop leads sign-off
SERVICE_INTERVAL_KM = 30000
SERVICE_INTERVAL_KM_PASSENGER = 20000
SERVICE_INTERVAL_MONTHS = 6
EV_KM_INTERVAL = 40000
EV_MONTHS_INTERVAL = 12
RETIRE_KM = 220000
OVERDUE_GRACE_DAYS = 14


def _last_service(records: list[ServiceRecord]) -> ServiceRecord | None:
    if not records:
        return None
    return sorted(records, key=lambda r: r.service_date)[-1]


def next_service(vehicle: Vehicle, records: list[ServiceRecord], today: date) -> tuple[date, int]:
    last = _last_service(records)
    if last is None:
        return (today, vehicle.mileage_km)

    last_date = last.service_date
    last_km = last.mileage_at_service

    if vehicle.vehicle_class == VehicleClass.passenger:
        km_interval = SERVICE_INTERVAL_KM_PASSENGER
    elif vehicle.vehicle_class == VehicleClass.ev:
        km_interval = EV_KM_INTERVAL
    else:
        km_interval = SERVICE_INTERVAL_KM

    months = EV_MONTHS_INTERVAL if vehicle.vehicle_class == VehicleClass.ev else SERVICE_INTERVAL_MONTHS

    # Preserve legacy month arithmetic (not relativedelta) including the feb hack
    m = last_date.month + months
    y = last_date.year
    while m > 12:
        m -= 12
        y += 1
    try:
        due_date = datetime.date(y, m, last_date.day)
    except ValueError:
        due_date = datetime.date(y, m, 28)  # feb hack

    return (due_date, last_km + km_interval)


def status(vehicle: Vehicle, records: list[ServiceRecord], today: date) -> VehicleStatus:
    if vehicle.mileage_km >= RETIRE_KM:
        return VehicleStatus.retired

    due_date, due_km = next_service(vehicle, records, today)

    if vehicle.mileage_km >= due_km:
        return VehicleStatus.overdue

    if today > due_date:
        delta = (today - due_date).days
        if delta > OVERDUE_GRACE_DAYS:
            return VehicleStatus.overdue
        return VehicleStatus.maintenance

    # Preserve legacy quirk: negative (today - last_date).days satisfies <= 3
    last = _last_service(records)
    if last and (today - last.service_date).days <= 3:
        return VehicleStatus.maintenance

    return VehicleStatus.active


def priority(vehicle: Vehicle, records: list[ServiceRecord], today: date) -> int:
    if status(vehicle, records, today) == VehicleStatus.retired:
        return 0

    due_date, due_km = next_service(vehicle, records, today)
    days_over = (today - due_date).days
    km_over = vehicle.mileage_km - due_km

    score = 0
    if days_over > 0:
        score += min(days_over, 60)
    if km_over > 0:
        score += min(km_over // 250, 40)
    if vehicle.vehicle_class == VehicleClass.commercial:
        score += 10

    return min(score, 100)
