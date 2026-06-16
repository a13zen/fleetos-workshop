import sys
import os
from datetime import date

# legacy_fleettracker/ is not a package; add it to path so app.py can import db_utils
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "starter", "legacy_fleettracker")
)

from app import calc_next_service, calc_status, calc_priority
import db_utils

TODAY = date(2025, 11, 1)


def _v(vid):
    return db_utils.get_vehicle(vid)


# ---------------------------------------------------------------------------
# VH-0096 - commercial - 72440 km - last service 2025-10-30 (2 days before TODAY)
# ---------------------------------------------------------------------------

def test_vh0096_next_service():
    assert calc_next_service(_v("VH-0096"), TODAY) == (date(2026, 4, 30), 100900)


def test_vh0096_status_maintenance_in_shop():
    # (TODAY - 2025-10-30).days == 2, satisfies the <= 3 in-shop guard
    assert calc_status(_v("VH-0096"), TODAY) == "maintenance"


def test_vh0096_priority():
    # Not overdue by date or km; commercial class adds flat +10
    assert calc_priority(_v("VH-0096"), TODAY) == 10


# ---------------------------------------------------------------------------
# VH-0017 - commercial - 156430 km - last service 2025-09-03
# ---------------------------------------------------------------------------

def test_vh0017_next_service():
    assert calc_next_service(_v("VH-0017"), TODAY) == (date(2026, 3, 3), 181900)


def test_vh0017_status_active():
    assert calc_status(_v("VH-0017"), TODAY) == "active"


def test_vh0017_priority():
    assert calc_priority(_v("VH-0017"), TODAY) == 10


# ---------------------------------------------------------------------------
# VH-0058 - ev - 18760 km - last service 2026-03-30 (FUTURE record in CSV)
#
# _last_service() does not filter by date - the 2026-03-30 record sorts last.
# (TODAY - date(2026,3,30)).days == -149, which satisfies (<= 3) -> "maintenance".
# This is a known quirk: record as-is.
# ---------------------------------------------------------------------------

def test_vh0058_next_service():
    assert calc_next_service(_v("VH-0058"), TODAY) == (date(2027, 3, 30), 58200)


def test_vh0058_status_maintenance_future_record_quirk():
    # Negative days (-149) satisfies the <= 3 in-shop guard -> "maintenance" despite not being in shop
    assert calc_status(_v("VH-0058"), TODAY) == "maintenance"


def test_vh0058_priority():
    # EV class; not overdue; no commercial bump
    assert calc_priority(_v("VH-0058"), TODAY) == 0


# ---------------------------------------------------------------------------
# VH-0023 - passenger - 119870 km - last service 2025-09-28
# ---------------------------------------------------------------------------

def test_vh0023_next_service():
    assert calc_next_service(_v("VH-0023"), TODAY) == (date(2026, 3, 28), 137300)


def test_vh0023_status_active():
    assert calc_status(_v("VH-0023"), TODAY) == "active"


def test_vh0023_priority():
    assert calc_priority(_v("VH-0023"), TODAY) == 0


# ---------------------------------------------------------------------------
# VH-0050 - passenger - 241300 km - highest mileage in fleet (RETIRED)
# No vehicle in the CSV has zero service records.
# ---------------------------------------------------------------------------

def test_vh0050_next_service():
    # calc_next_service is called without the km check; still computes normally
    assert calc_next_service(_v("VH-0050"), TODAY) == (date(2025, 10, 9), 260100)


def test_vh0050_status_retired():
    assert calc_status(_v("VH-0050"), TODAY) == "retired"


def test_vh0050_priority_zero():
    # Retired vehicles always score 0
    assert calc_priority(_v("VH-0050"), TODAY) == 0


# ---------------------------------------------------------------------------
# VH-0029 - commercial - 178650 km - high mileage, last service 2025-08-22
# ---------------------------------------------------------------------------

def test_vh0029_next_service():
    assert calc_next_service(_v("VH-0029"), TODAY) == (date(2026, 2, 22), 204200)


def test_vh0029_status_active():
    assert calc_status(_v("VH-0029"), TODAY) == "active"


def test_vh0029_priority():
    assert calc_priority(_v("VH-0029"), TODAY) == 10
