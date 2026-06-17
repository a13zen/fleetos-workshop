"""
Characterisation tests for the legacy FleetTracker maintenance functions AND
the new fleetos_api maintenance module.

These tests pin the *current* behaviour of calc_next_service, calc_status,
and calc_priority at a fixed date (2025-11-01) so that the FastAPI port can
be verified for identical output.

Golden rule: outputs are recorded AS-IS, including bugs (e.g. future-dated
service records causing vehicles to appear "in maintenance").

The parametrized TestAllVehiclesFullSuite class is run twice via
pytest.mark.parametrize on the ``impl`` fixture: once against the legacy
app.py functions and once against the new fleetos_api functions.
"""
import sys
import os
import datetime
import pytest

# ---------------------------------------------------------------------------
# Legacy imports
# ---------------------------------------------------------------------------
# Allow imports from legacy_fleettracker/ without installing it as a package.
_STARTER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGACY_DIR = os.path.join(_STARTER_DIR, "legacy_fleettracker")
if _LEGACY_DIR not in sys.path:
    sys.path.insert(0, _LEGACY_DIR)

_orig_cwd = os.getcwd()

import importlib

# Change to the legacy dir so that db_utils can find its data/ folder via
# __file__-relative paths, then import the modules.
os.chdir(_LEGACY_DIR)
import db_utils  # noqa: E402
import app as legacy_app  # noqa: E402
os.chdir(_orig_cwd)

# ---------------------------------------------------------------------------
# New fleetos_api imports
# ---------------------------------------------------------------------------
# Add starter/ to sys.path so fleetos_api package can be imported.
if _STARTER_DIR not in sys.path:
    sys.path.insert(0, _STARTER_DIR)

from fleetos_api.data_loader import load_vehicles, load_service_history
from fleetos_api import maintenance as fleetos_maintenance
from fleetos_api.models import Vehicle as FleetosVehicle, VehicleClass

TODAY = datetime.date(2025, 11, 1)

# Pre-load service history once for all new-API tests
_SERVICE_HISTORY = load_service_history()
_VEHICLES_BY_ID = {v.id: v for v in load_vehicles()}

# ---------------------------------------------------------------------------
# Helper: build a legacy vehicle dict as db_utils returns it (all strings).
# ---------------------------------------------------------------------------

def _vehicle(id_, make, model, year, vehicle_class, location, mileage_km, assigned_driver=""):
    return {
        "id": id_,
        "make": make,
        "model": model,
        "year": str(year),
        "vehicle_class": vehicle_class,
        "location": location,
        "mileage_km": str(mileage_km),
        "assigned_driver": assigned_driver,
    }


# ---------------------------------------------------------------------------
# Adapter: wrap the fleetos_api functions so they accept the same legacy-style
# vehicle dict and today parameter, returning the same types.
# ---------------------------------------------------------------------------

def _new_calc_next_service(vehicle_dict, today):
    v = _VEHICLES_BY_ID[vehicle_dict["id"]]
    return fleetos_maintenance.calc_next_service(v, _SERVICE_HISTORY, today)


def _new_calc_status(vehicle_dict, today):
    v = _VEHICLES_BY_ID[vehicle_dict["id"]]
    result = fleetos_maintenance.calc_status(v, _SERVICE_HISTORY, today)
    return result.value  # return string to match legacy


def _new_calc_priority(vehicle_dict, today):
    v = _VEHICLES_BY_ID[vehicle_dict["id"]]
    return fleetos_maintenance.calc_priority(v, _SERVICE_HISTORY, today)


# ---------------------------------------------------------------------------
# Vehicles selected to cover every vehicle_class, highest mileage, and the
# retired-threshold edge case.  All expected values were computed by running
# the legacy code at today=2025-11-01.
# ---------------------------------------------------------------------------

class TestCalcNextService:
    """Characterise calc_next_service for six representative vehicles."""

    def test_commercial_normal(self):
        """VH-0017: commercial, last service 2025-09-03 @ 151900 km."""
        v = _vehicle("VH-0017", "BMW", "X5", 2019, "commercial",
                     "Munich North Logistics Hub - Gate 14", 156430, "S. Vogel")
        # Legacy
        due_date, due_km = legacy_app.calc_next_service(v, TODAY)
        assert due_date == datetime.date(2026, 3, 3)
        assert due_km == 181900
        # New API
        new_due_date, new_due_km = _new_calc_next_service(v, TODAY)
        assert new_due_date == datetime.date(2026, 3, 3)
        assert new_due_km == 181900

    def test_commercial_future_service_date(self):
        """VH-0042: commercial, last service is 2026-01-12 (future at test date).
        Bug: future service records are accepted as the 'latest' service,
        producing a next-due date even further in the future."""
        v = _vehicle("VH-0042", "BMW", "3 Series Touring", 2021, "commercial",
                     "Hamburg Depot", 84210, "J. Brandt")
        due_date, due_km = legacy_app.calc_next_service(v, TODAY)
        assert due_date == datetime.date(2026, 7, 12)
        assert due_km == 113100
        new_due_date, new_due_km = _new_calc_next_service(v, TODAY)
        assert new_due_date == datetime.date(2026, 7, 12)
        assert new_due_km == 113100

    def test_passenger_normal(self):
        """VH-0071: passenger, last service 2026-04-10 @ 97200 km (future date).
        20,000 km interval; 6-month date interval."""
        v = _vehicle("VH-0071", "BMW", "1 Series", 2020, "passenger",
                     "Frankfurt Service Centre", 97540, "T. Roth")
        due_date, due_km = legacy_app.calc_next_service(v, TODAY)
        assert due_date == datetime.date(2026, 10, 10)
        assert due_km == 117200
        new_due_date, new_due_km = _new_calc_next_service(v, TODAY)
        assert new_due_date == datetime.date(2026, 10, 10)
        assert new_due_km == 117200

    def test_ev_interval(self):
        """VH-0058: EV, 40,000 km / 12-month interval per 2021 memo."""
        v = _vehicle("VH-0058", "BMW", "iX1", 2024, "ev",
                     "Stuttgart Sued", 18760, "A. Lehmann")
        due_date, due_km = legacy_app.calc_next_service(v, TODAY)
        assert due_date == datetime.date(2027, 3, 30)
        assert due_km == 58200
        new_due_date, new_due_km = _new_calc_next_service(v, TODAY)
        assert new_due_date == datetime.date(2027, 3, 30)
        assert new_due_km == 58200

    def test_retired_vehicle_still_returns_next_service(self):
        """VH-0009: mileage 224980 >= 220000 (retired), but calc_next_service
        still returns a date/km tuple regardless of retirement status."""
        v = _vehicle("VH-0009", "BMW", "5 Series Touring", 2018, "passenger",
                     "Dingolfing Yard", 224980)
        due_date, due_km = legacy_app.calc_next_service(v, TODAY)
        assert due_date == datetime.date(2025, 12, 14)
        assert due_km == 243900
        new_due_date, new_due_km = _new_calc_next_service(v, TODAY)
        assert new_due_date == datetime.date(2025, 12, 14)
        assert new_due_km == 243900

    def test_highest_mileage_vehicle(self):
        """VH-0050: 241300 km — highest mileage in fleet, well above retire threshold."""
        v = _vehicle("VH-0050", "BMW", "1 Series", 2017, "passenger",
                     "Dingolfing Yard", 241300)
        due_date, due_km = legacy_app.calc_next_service(v, TODAY)
        assert due_date == datetime.date(2025, 10, 9)
        assert due_km == 260100
        new_due_date, new_due_km = _new_calc_next_service(v, TODAY)
        assert new_due_date == datetime.date(2025, 10, 9)
        assert new_due_km == 260100


class TestCalcStatus:
    """Characterise calc_status for the same six vehicles."""

    def test_commercial_active(self):
        """VH-0017: not overdue by km or date, not recently serviced -> active."""
        v = _vehicle("VH-0017", "BMW", "X5", 2019, "commercial",
                     "Munich North Logistics Hub - Gate 14", 156430, "S. Vogel")
        assert legacy_app.calc_status(v, TODAY) == "active"
        assert _new_calc_status(v, TODAY) == "active"

    def test_commercial_future_service_maintenance_bug(self):
        """VH-0042: last service is 2026-01-12 (future).
        Bug: (today - future_date).days is negative, which is <= 3, so the
        'currently in shop' branch fires and returns 'maintenance'."""
        v = _vehicle("VH-0042", "BMW", "3 Series Touring", 2021, "commercial",
                     "Hamburg Depot", 84210, "J. Brandt")
        assert legacy_app.calc_status(v, TODAY) == "maintenance"
        assert _new_calc_status(v, TODAY) == "maintenance"

    def test_passenger_future_service_maintenance_bug(self):
        """VH-0071: same future-service bug."""
        v = _vehicle("VH-0071", "BMW", "1 Series", 2020, "passenger",
                     "Frankfurt Service Centre", 97540, "T. Roth")
        assert legacy_app.calc_status(v, TODAY) == "maintenance"
        assert _new_calc_status(v, TODAY) == "maintenance"

    def test_ev_future_service_maintenance_bug(self):
        """VH-0058: EV with future last service date."""
        v = _vehicle("VH-0058", "BMW", "iX1", 2024, "ev",
                     "Stuttgart Sued", 18760, "A. Lehmann")
        assert legacy_app.calc_status(v, TODAY) == "maintenance"
        assert _new_calc_status(v, TODAY) == "maintenance"

    def test_retired_by_mileage(self):
        """VH-0009: mileage 224980 >= RETIRE_KM 220000 -> retired."""
        v = _vehicle("VH-0009", "BMW", "5 Series Touring", 2018, "passenger",
                     "Dingolfing Yard", 224980)
        assert legacy_app.calc_status(v, TODAY) == "retired"
        assert _new_calc_status(v, TODAY) == "retired"

    def test_highest_mileage_retired(self):
        """VH-0050: 241300 km -> retired."""
        v = _vehicle("VH-0050", "BMW", "1 Series", 2017, "passenger",
                     "Dingolfing Yard", 241300)
        assert legacy_app.calc_status(v, TODAY) == "retired"
        assert _new_calc_status(v, TODAY) == "retired"


class TestCalcPriority:
    """Characterise calc_priority for the same six vehicles."""

    def test_commercial_active_gets_class_bump(self):
        """VH-0017: active, not overdue, commercial -> score 0 + 10 (commercial bump) = 10."""
        v = _vehicle("VH-0017", "BMW", "X5", 2019, "commercial",
                     "Munich North Logistics Hub - Gate 14", 156430, "S. Vogel")
        assert legacy_app.calc_priority(v, TODAY) == 10
        assert _new_calc_priority(v, TODAY) == 10

    def test_commercial_maintenance_gets_class_bump(self):
        """VH-0042: maintenance status (future-date bug), not past due_date from
        today's perspective (due 2026-07-12), so days_over <= 0; km also under
        due_km -> base score 0 + 10 commercial = 10."""
        v = _vehicle("VH-0042", "BMW", "3 Series Touring", 2021, "commercial",
                     "Hamburg Depot", 84210, "J. Brandt")
        assert legacy_app.calc_priority(v, TODAY) == 10
        assert _new_calc_priority(v, TODAY) == 10

    def test_passenger_maintenance_no_bump(self):
        """VH-0071: maintenance, passenger -> 0 (no class bump, not overdue)."""
        v = _vehicle("VH-0071", "BMW", "1 Series", 2020, "passenger",
                     "Frankfurt Service Centre", 97540, "T. Roth")
        assert legacy_app.calc_priority(v, TODAY) == 0
        assert _new_calc_priority(v, TODAY) == 0

    def test_ev_maintenance_no_bump(self):
        """VH-0058: maintenance, ev -> 0."""
        v = _vehicle("VH-0058", "BMW", "iX1", 2024, "ev",
                     "Stuttgart Sued", 18760, "A. Lehmann")
        assert legacy_app.calc_priority(v, TODAY) == 0
        assert _new_calc_priority(v, TODAY) == 0

    def test_retired_priority_zero(self):
        """VH-0009: retired -> priority always 0."""
        v = _vehicle("VH-0009", "BMW", "5 Series Touring", 2018, "passenger",
                     "Dingolfing Yard", 224980)
        assert legacy_app.calc_priority(v, TODAY) == 0
        assert _new_calc_priority(v, TODAY) == 0

    def test_highest_mileage_retired_priority_zero(self):
        """VH-0050: retired -> 0."""
        v = _vehicle("VH-0050", "BMW", "1 Series", 2017, "passenger",
                     "Dingolfing Yard", 241300)
        assert legacy_app.calc_priority(v, TODAY) == 0
        assert _new_calc_priority(v, TODAY) == 0


class TestAllVehiclesFullSuite:
    """Full golden-dataset sweep: all 18 vehicles, all three functions.
    Values computed by running legacy code at today=2025-11-01.
    Each parametrized case is asserted against BOTH legacy and new API."""

    GOLDEN = [
        # (id, vehicle_class, mileage, due_date, due_km, status, priority)
        ("VH-0042", "commercial",  84210, datetime.date(2026,  7, 12), 113100, "maintenance", 10),
        ("VH-0017", "commercial", 156430, datetime.date(2026,  3,  3), 181900, "active",      10),
        ("VH-0103", "commercial",  41120, datetime.date(2026,  8, 20),  70100, "maintenance", 10),
        ("VH-0058", "ev",          18760, datetime.date(2027,  3, 30),  58200, "maintenance",  0),
        ("VH-0009", "passenger",  224980, datetime.date(2025, 12, 14), 243900, "retired",      0),
        ("VH-0071", "passenger",   97540, datetime.date(2026, 10, 10), 117200, "maintenance",  0),
        ("VH-0126", "commercial", 142200, datetime.date(2026,  4,  1), 168500, "active",      10),
        ("VH-0064", "passenger",   63310, datetime.date(2026,  5, 18),  81900, "maintenance",  0),
        ("VH-0033", "commercial", 131870, datetime.date(2026, 10,  8), 161500, "maintenance", 10),
        ("VH-0081", "passenger",   38420, datetime.date(2026,  6,  5),  57200, "maintenance",  0),
        ("VH-0029", "commercial", 178650, datetime.date(2026,  2, 22), 204200, "active",      10),
        ("VH-0140", "ev",           9120, datetime.date(2027,  1, 28),  48400, "maintenance",  0),
        ("VH-0096", "commercial",  72440, datetime.date(2026,  4, 30), 100900, "maintenance", 10),
        ("VH-0050", "passenger",  241300, datetime.date(2025, 10,  9), 260100, "retired",      0),
        ("VH-0112", "commercial",  27540, datetime.date(2026,  8,  2),  56600, "maintenance", 10),
        ("VH-0023", "passenger",  119870, datetime.date(2026,  3, 28), 137300, "active",       0),
        ("VH-0135", "passenger",   22890, datetime.date(2026, 10, 12),  42500, "maintenance",  0),
        ("VH-0077", "commercial",  55630, datetime.date(2026,  5,  4),  84100, "maintenance", 10),
    ]

    # Vehicle details needed to reconstruct the dict (make/model/location/driver
    # don't affect maintenance logic but are included for completeness).
    _DETAILS = {
        "VH-0042": ("BMW", "3 Series Touring", 2021, "Hamburg Depot", "J. Brandt"),
        "VH-0017": ("BMW", "X5", 2019, "Munich North Logistics Hub - Gate 14", "S. Vogel"),
        "VH-0103": ("BMW", "X1", 2022, "Berlin Tempelhof", "M. Krueger"),
        "VH-0058": ("BMW", "iX1", 2024, "Stuttgart Sued", "A. Lehmann"),
        "VH-0009": ("BMW", "5 Series Touring", 2018, "Dingolfing Yard", ""),
        "VH-0071": ("BMW", "1 Series", 2020, "Frankfurt Service Centre", "T. Roth"),
        "VH-0126": ("BMW", "X5", 2020, "Dingolfing Distribution Centre - Dock 3", "K. Hofmann"),
        "VH-0064": ("BMW", "X3", 2021, "Duesseldorf", "L. Fischer"),
        "VH-0033": ("BMW", "3 Series Touring", 2019, "Leipzig Service Centre", "P. Neumann"),
        "VH-0081": ("BMW", "4 Series Gran Coupe", 2022, "Koeln Innenstadt", "C. Wagner"),
        "VH-0029": ("BMW", "X1", 2018, "Bremen Hafen", "R. Schulz"),
        "VH-0140": ("BMW", "iX1", 2025, "Nuernberg Ost", "E. Becker"),
        "VH-0096": ("BMW", "X5", 2021, "Dresden", "N. Hartmann"),
        "VH-0050": ("BMW", "1 Series", 2017, "Dingolfing Yard", ""),
        "VH-0112": ("BMW", "3 Series Touring", 2023, "Hannover Messe - Hall 9", "F. Lorenz"),
        "VH-0023": ("BMW", "5 Series Touring", 2020, "Dortmund", "I. Keller"),
        "VH-0135": ("BMW", "X3", 2023, "Muenchen Service Centre", "D. Sommer"),
        "VH-0077": ("BMW", "X1", 2021, "Essen", "H. Winter"),
    }

    @pytest.mark.parametrize("vid,cls,mileage,exp_date,exp_km,exp_status,exp_prio", GOLDEN)
    def test_full_golden_dataset(self, vid, cls, mileage, exp_date, exp_km, exp_status, exp_prio):
        make, model, year, location, driver = self._DETAILS[vid]
        v = _vehicle(vid, make, model, year, cls, location, mileage, driver)

        # --- Legacy assertions ---
        due_date, due_km = legacy_app.calc_next_service(v, TODAY)
        assert due_date == exp_date, f"{vid} (legacy): due_date mismatch"
        assert due_km == exp_km, f"{vid} (legacy): due_km mismatch"
        assert legacy_app.calc_status(v, TODAY) == exp_status, f"{vid} (legacy): status mismatch"
        assert legacy_app.calc_priority(v, TODAY) == exp_prio, f"{vid} (legacy): priority mismatch"

        # --- New API assertions ---
        new_due_date, new_due_km = _new_calc_next_service(v, TODAY)
        assert new_due_date == exp_date, f"{vid} (new api): due_date mismatch"
        assert new_due_km == exp_km, f"{vid} (new api): due_km mismatch"
        assert _new_calc_status(v, TODAY) == exp_status, f"{vid} (new api): status mismatch"
        assert _new_calc_priority(v, TODAY) == exp_prio, f"{vid} (new api): priority mismatch"
