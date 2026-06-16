from datetime import date

from fleetos_api.data_loader import get_service_records, get_vehicle
from fleetos_api.maintenance import next_service, priority, status
from fleetos_api.models import VehicleStatus

TODAY = date(2025, 11, 1)


def _v(vid):
    return get_vehicle(vid)


def _r(vid):
    return get_service_records(vid)


# ---------------------------------------------------------------------------
# VH-0096 - commercial - 72440 km - last service 2025-10-30 (2 days before TODAY)
# ---------------------------------------------------------------------------

def test_vh0096_next_service():
    assert next_service(_v("VH-0096"), _r("VH-0096"), TODAY) == (date(2026, 4, 30), 100900)


def test_vh0096_status_maintenance_in_shop():
    assert status(_v("VH-0096"), _r("VH-0096"), TODAY) == VehicleStatus.maintenance


def test_vh0096_priority():
    assert priority(_v("VH-0096"), _r("VH-0096"), TODAY) == 10


# ---------------------------------------------------------------------------
# VH-0017 - commercial - 156430 km - last service 2025-09-03
# ---------------------------------------------------------------------------

def test_vh0017_next_service():
    assert next_service(_v("VH-0017"), _r("VH-0017"), TODAY) == (date(2026, 3, 3), 181900)


def test_vh0017_status_active():
    assert status(_v("VH-0017"), _r("VH-0017"), TODAY) == VehicleStatus.active


def test_vh0017_priority():
    assert priority(_v("VH-0017"), _r("VH-0017"), TODAY) == 10


# ---------------------------------------------------------------------------
# VH-0058 - ev - 18760 km - last service 2026-03-30 (FUTURE record in CSV)
# Quirk preserved: negative (TODAY - last_date).days satisfies <= 3 -> maintenance
# ---------------------------------------------------------------------------

def test_vh0058_next_service():
    assert next_service(_v("VH-0058"), _r("VH-0058"), TODAY) == (date(2027, 3, 30), 58200)


def test_vh0058_status_maintenance_future_record_quirk():
    assert status(_v("VH-0058"), _r("VH-0058"), TODAY) == VehicleStatus.maintenance


def test_vh0058_priority():
    assert priority(_v("VH-0058"), _r("VH-0058"), TODAY) == 0


# ---------------------------------------------------------------------------
# VH-0023 - passenger - 119870 km - last service 2025-09-28
# ---------------------------------------------------------------------------

def test_vh0023_next_service():
    assert next_service(_v("VH-0023"), _r("VH-0023"), TODAY) == (date(2026, 3, 28), 137300)


def test_vh0023_status_active():
    assert status(_v("VH-0023"), _r("VH-0023"), TODAY) == VehicleStatus.active


def test_vh0023_priority():
    assert priority(_v("VH-0023"), _r("VH-0023"), TODAY) == 0


# ---------------------------------------------------------------------------
# VH-0050 - passenger - 241300 km - highest mileage (RETIRED)
# ---------------------------------------------------------------------------

def test_vh0050_next_service():
    assert next_service(_v("VH-0050"), _r("VH-0050"), TODAY) == (date(2025, 10, 9), 260100)


def test_vh0050_status_retired():
    assert status(_v("VH-0050"), _r("VH-0050"), TODAY) == VehicleStatus.retired


def test_vh0050_priority_zero():
    assert priority(_v("VH-0050"), _r("VH-0050"), TODAY) == 0


# ---------------------------------------------------------------------------
# VH-0029 - commercial - 178650 km - high mileage, last service 2025-08-22
# ---------------------------------------------------------------------------

def test_vh0029_next_service():
    assert next_service(_v("VH-0029"), _r("VH-0029"), TODAY) == (date(2026, 2, 22), 204200)


def test_vh0029_status_active():
    assert status(_v("VH-0029"), _r("VH-0029"), TODAY) == VehicleStatus.active


def test_vh0029_priority():
    assert priority(_v("VH-0029"), _r("VH-0029"), TODAY) == 10
