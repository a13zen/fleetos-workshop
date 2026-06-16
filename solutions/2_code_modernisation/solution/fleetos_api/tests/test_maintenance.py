from datetime import date

from fleetos_api.maintenance import next_service, priority, status
from fleetos_api.models import ServiceRecord, Vehicle, VehicleClass, VehicleStatus

TODAY = date(2025, 11, 1)


def _vehicle(vid="VH-TEST", vehicle_class=VehicleClass.commercial, mileage_km=50000):
    return Vehicle(
        id=vid, make="BMW", model="Test", year=2020,
        vehicle_class=vehicle_class, location="Depot",
        mileage_km=mileage_km, assigned_driver=None,
    )


def _record(service_date=date(2025, 5, 1), mileage_at_service=20000, vid="VH-TEST"):
    return ServiceRecord(
        vehicle_id=vid, service_date=service_date,
        mileage_at_service=mileage_at_service,
        work_performed="Oil change", cost_eur=250.0,
    )


# ---------------------------------------------------------------------------
# EV: 40,000 km / 12-month intervals
# ---------------------------------------------------------------------------

def test_ev_km_interval():
    v = _vehicle(vehicle_class=VehicleClass.ev, mileage_km=30000)
    r = [_record(service_date=date(2024, 5, 1), mileage_at_service=10000)]
    _, due_km = next_service(v, r, TODAY)
    assert due_km == 10000 + 40000


def test_ev_month_interval():
    v = _vehicle(vehicle_class=VehicleClass.ev, mileage_km=30000)
    r = [_record(service_date=date(2024, 5, 1), mileage_at_service=10000)]
    due_date, _ = next_service(v, r, TODAY)
    assert due_date == date(2025, 5, 1)


# ---------------------------------------------------------------------------
# Grace window boundary: 14 days -> maintenance, 15 days -> overdue
#
# commercial, last service date(2025, 4, 18) -> due_date date(2025, 10, 18)
# (TODAY - date(2025, 10, 18)).days == 14
# ---------------------------------------------------------------------------

def test_grace_day_14_is_maintenance():
    # delta == OVERDUE_GRACE_DAYS (14): still in grace window
    v = _vehicle(mileage_km=30000)
    r = [_record(service_date=date(2025, 4, 18), mileage_at_service=10000)]
    # due_date = date(2025, 10, 18), (TODAY - due_date).days = 14
    assert status(v, r, TODAY) == VehicleStatus.maintenance


def test_grace_day_15_is_overdue():
    # delta == OVERDUE_GRACE_DAYS + 1 (15): past grace window
    v = _vehicle(mileage_km=30000)
    r = [_record(service_date=date(2025, 4, 17), mileage_at_service=10000)]
    # due_date = date(2025, 10, 17), (TODAY - due_date).days = 15
    assert status(v, r, TODAY) == VehicleStatus.overdue


# ---------------------------------------------------------------------------
# Retirement threshold: 220,000 km
# ---------------------------------------------------------------------------

def test_just_below_retirement_is_not_retired():
    v = _vehicle(mileage_km=219999)
    r = [_record(service_date=date(2025, 4, 1), mileage_at_service=190000)]
    assert status(v, r, TODAY) != VehicleStatus.retired


def test_at_retirement_threshold_is_retired():
    v = _vehicle(mileage_km=220000)
    r = [_record(service_date=date(2025, 4, 1), mileage_at_service=190000)]
    assert status(v, r, TODAY) == VehicleStatus.retired


def test_retired_priority_is_zero():
    v = _vehicle(mileage_km=220000)
    r = [_record(service_date=date(2025, 4, 1), mileage_at_service=190000)]
    assert priority(v, r, TODAY) == 0


# ---------------------------------------------------------------------------
# Commercial +10 priority bump
# ---------------------------------------------------------------------------

def test_commercial_priority_bump():
    # Not overdue by date or km; commercial class adds +10
    v = _vehicle(vehicle_class=VehicleClass.commercial, mileage_km=30000)
    r = [_record(service_date=date(2025, 9, 1), mileage_at_service=20000)]
    assert priority(v, r, TODAY) == 10


def test_passenger_has_no_commercial_bump():
    # Same situation but passenger -> 0
    v = _vehicle(vehicle_class=VehicleClass.passenger, mileage_km=30000)
    r = [_record(service_date=date(2025, 9, 1), mileage_at_service=20000)]
    assert priority(v, r, TODAY) == 0


def test_ev_has_no_commercial_bump():
    v = _vehicle(vehicle_class=VehicleClass.ev, mileage_km=20000)
    r = [_record(service_date=date(2025, 9, 1), mileage_at_service=10000)]
    assert priority(v, r, TODAY) == 0


# ---------------------------------------------------------------------------
# Priority cap at 100
#
# Setup: commercial, days_over=65 -> min(65,60)=60, km_over=10000 -> min(40,40)=40
# 60 + 40 + 10 (commercial) = 110 -> capped at 100
#
# last service date(2025, 2, 28) -> due_date date(2025, 8, 28)
# (TODAY - date(2025, 8, 28)).days = 65
# last_km=20000, due_km=50000, vehicle mileage=60000 -> km_over=10000
# ---------------------------------------------------------------------------

def test_priority_capped_at_100():
    v = _vehicle(vehicle_class=VehicleClass.commercial, mileage_km=60000)
    r = [_record(service_date=date(2025, 2, 28), mileage_at_service=20000)]
    assert priority(v, r, TODAY) == 100


# ---------------------------------------------------------------------------
# No service history: due immediately at current mileage -> overdue
# ---------------------------------------------------------------------------

def test_no_history_next_service_due_now():
    v = _vehicle(mileage_km=50000)
    assert next_service(v, [], TODAY) == (TODAY, 50000)


def test_no_history_status_is_overdue():
    v = _vehicle(mileage_km=50000)
    # due_km == mileage_km -> overdue
    assert status(v, [], TODAY) == VehicleStatus.overdue
