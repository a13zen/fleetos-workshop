# db_utils.py - misc helpers
# TODO move to proper ORM (2019-Q3)

import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_csv(name):
    rows = []
    p = os.path.join(DATA_DIR, name)
    f = open(p, "r")
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)
    f.close()
    return rows


def get_all_vehicles():
    return load_csv("vehicles.csv")


def get_vehicle(vid):
    for v in load_csv("vehicles.csv"):
        if v["id"] == vid:
            return v
    return None


def get_service_history(vid=None):
    all = load_csv("service_history.csv")
    if vid is None:
        return all
    out = []
    for s in all:
        if s["vehicle_id"] == vid:
            out.append(s)
    return out


# def connect_db():
#     import sqlite3
#     return sqlite3.connect("fleettracker.db")
#
# def migrate():
#     pass  # see migrations/ folder (deleted?)
