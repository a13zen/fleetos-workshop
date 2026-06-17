"""Pure maintenance logic.  No I/O.  Every public function takes an explicit
``today: date`` parameter so results are deterministic and testable.

All business rules are intentionally identical to the legacy app.py functions,
including known quirks (future service-date bug, feb-28 hack, etc.).
"""
from __future__ import annotations

import datetime
from typing import List, Optional, Tuple

from fleetos_api.models import Vehicle, ServiceRecord, VehicleClass, VehicleStatus

# --- constants (identical to legacy) ----------------------------------------
SERVICE_INTERVAL_KM = 30000           # commercial default
SERVICE_INTERVAL_KM_PASSENGER = 20000
SERVICE_INTERVAL_MONTHS = 6
RETIRE_KM = 220000
OVERDUE_GRACE_DAYS = 14


def _last_service(
    vehicle_id: str, service_history: List[ServiceRecord]
) -> Optional[ServiceRecord]:
    """Return the most recent service record for this vehicle, or None."""
    records = [r for r in service_history if r.vehicle_id == vehicle_id]
    if not records:
        return None
    return sorted(records, key=lambda r: r.service_date)[-1]


def calc_next_service(
    vehicle: Vehicle,
    service_history: List[ServiceRecord],
    today: datetime.date,
) -> Tuple[datetime.date, int]:
    """Compute (due_date, due_km) for the vehicle.

    Replicates legacy calc_next_service exactly, including:
    - EV uses 40000 km / 12 months (per 2021 memo)
    - No service history: due date = today, due_km = current mileage
    - Feb-28 fallback for month-end overflow
    - Future service dates are accepted as-is (known bug preserved)
    """
    last = _last_service(vehicle.id, service_history)
    if last is None:
        return (today, vehicle.mileage_km)

    last_date = last.service_date
    last_km = last.mileage_at_service

    cls = vehicle.vehicle_class.value
    if cls == "passenger":
        km_interval = SERVICE_INTERVAL_KM_PASSENGER
    elif cls == "ev":
        km_interval = 40000
    else:
        km_interval = SERVICE_INTERVAL_KM

    months = SERVICE_INTERVAL_MONTHS
    if cls == "ev":
        months = 12

    # Date-based due — roll months forward (legacy manual month arithmetic)
    m = last_date.month + months
    y = last_date.year
    while m > 12:
        m = m - 12
        y = y + 1
    try:
        due_date = datetime.date(y, m, last_date.day)
    except ValueError:
        due_date = datetime.date(y, m, 28)  # feb hack

    due_km = last_km + km_interval
    return (due_date, due_km)


def calc_status(
    vehicle: Vehicle,
    service_history: List[ServiceRecord],
    today: datetime.date,
) -> VehicleStatus:
    """Return vehicle status, replicating legacy calc_status exactly.

    Known quirks preserved:
    - Future service records make (today - last_service_date).days <= 3 evaluate
      to True (because the difference is negative), triggering "maintenance".
    """
    km = vehicle.mileage_km
    if km >= RETIRE_KM:
        return VehicleStatus.retired

    due_date, due_km = calc_next_service(vehicle, service_history, today)

    if km >= due_km:
        return VehicleStatus.overdue

    if today > due_date:
        delta = (today - due_date).days
        if delta > OVERDUE_GRACE_DAYS:
            return VehicleStatus.overdue
        else:
            return VehicleStatus.maintenance

    # Check if currently in shop (last service within 3 days)
    last = _last_service(vehicle.id, service_history)
    if last:
        ld = last.service_date
        if (today - ld).days <= 3:
            return VehicleStatus.maintenance

    return VehicleStatus.active


def calc_priority(
    vehicle: Vehicle,
    service_history: List[ServiceRecord],
    today: datetime.date,
) -> int:
    """Return priority 0-100, replicating legacy calc_priority exactly."""
    s = calc_status(vehicle, service_history, today)
    if s == VehicleStatus.retired:
        return 0

    due_date, due_km = calc_next_service(vehicle, service_history, today)
    km = vehicle.mileage_km
    days_over = (today - due_date).days
    km_over = km - due_km

    score = 0
    if days_over > 0:
        score = score + min(days_over, 60)
    if km_over > 0:
        score = score + min(km_over // 250, 40)
    if vehicle.vehicle_class.value == "commercial":
        score = score + 10  # vans earn money, prioritise
    if score > 100:
        score = 100
    return score
