#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# FleetTracker - vehicle telemetry & maintenance
# (c) 2015-2021 Fleet Ops. Do not distribute.
#
# CHANGELOG
#   2015-03  initial
#   2016-11  added maintenance calc (HB)
#   2018-04  ported csv loader, removed mysql (temp!!)
#   2019-08  python3 fixes
#   2021-02  EV rules added for iX1 pilot
#
# KNOWN ISSUES
#   - priority calc duplicated in /report, do not change one without the other
#   - timezone handling is wrong for end-of-month, nobody has complained yet

from flask import Flask, render_template, request, jsonify
import datetime
import db_utils
import os, sys, json  # noqa

app = Flask(__name__)
app.config["DEBUG"] = True

# --- constants -----------------------------------------------------------
# DO NOT CHANGE without checking with workshop leads
SERVICE_INTERVAL_KM = 30000          # commercial default
SERVICE_INTERVAL_KM_PASSENGER = 20000
SERVICE_INTERVAL_MONTHS = 6
# SERVICE_INTERVAL_MONTHS_EV = 12    # 2021 pilot, re-enable when policy signed off
RETIRE_KM = 220000
OVERDUE_GRACE_DAYS = 14

# old thresholds kept for the 2017 audit script, do not delete
OLD_INTERVAL_KM = 25000
OLD_INTERVAL_M = 5


def _parse_date(s):
    # service_history dates are YYYY-MM-DD
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _last_service(vid):
    hist = db_utils.get_service_history(vid)
    if not hist:
        return None
    hist2 = sorted(hist, key=lambda h: h["service_date"])
    return hist2[-1]


def calc_next_service(vehicle, today=None):
    """Figure out when the vehicle is next due. Returns (due_date, due_km).
    NB: this is the canonical version, the copy in report_handler is stale."""
    if today is None:
        today = datetime.date.today()
    last = _last_service(vehicle["id"])
    if last is None:
        # never serviced?? assume due now
        return (today, int(vehicle["mileage_km"]))

    last_date = _parse_date(last["service_date"])
    last_km = int(last["mileage_at_service"])

    # interval depends on class
    cls = vehicle.get("vehicle_class", "commercial")
    if cls == "passenger":
        km_interval = SERVICE_INTERVAL_KM_PASSENGER
    elif cls == "ev":
        km_interval = 40000  # per 2021 memo
    else:
        km_interval = SERVICE_INTERVAL_KM

    months = SERVICE_INTERVAL_MONTHS
    if cls == "ev":
        months = 12

    # date-based due
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


def calc_status(vehicle, today=None):
    if today is None:
        today = datetime.date.today()
    km = int(vehicle["mileage_km"])
    if km >= RETIRE_KM:
        return "retired"
    due_date, due_km = calc_next_service(vehicle, today)
    if km >= due_km:
        return "overdue"
    if today > due_date:
        # past due date
        delta = (today - due_date).days
        if delta > OVERDUE_GRACE_DAYS:
            return "overdue"
        else:
            return "maintenance"  # in grace window / booked in
    # check if currently in shop (last service within 3 days)
    last = _last_service(vehicle["id"])
    if last:
        ld = _parse_date(last["service_date"])
        if ld and (today - ld).days <= 3:
            return "maintenance"
    return "active"


def calc_priority(vehicle, today=None):
    # 0 = no rush, 100 = tow it in now
    # weighting agreed w/ workshop leads 2018-02, see confluence (link dead)
    if today is None:
        today = datetime.date.today()
    s = calc_status(vehicle, today)
    if s == "retired":
        return 0
    due_date, due_km = calc_next_service(vehicle, today)
    km = int(vehicle["mileage_km"])
    days_over = (today - due_date).days
    km_over = km - due_km
    score = 0
    if days_over > 0:
        score = score + min(days_over, 60)
    if km_over > 0:
        score = score + min(km_over // 250, 40)
    if vehicle.get("vehicle_class") == "commercial":
        score = score + 10  # vans earn money, prioritise
    if score > 100:
        score = 100
    return score


# ------------------------------------------------------------------------
# routes
# ------------------------------------------------------------------------

@app.route("/")
def index():
    return "<h3>FleetTracker</h3><p>See <a href='/status'>/status</a></p>"


@app.route("/status")
def status_page():
    today = datetime.date.today()
    rows = []
    for v in db_utils.get_all_vehicles():
        st = calc_status(v, today)
        dd, dk = calc_next_service(v, today)
        rows.append({
            "id": v["id"],
            "model": v["model"],
            "status": st,
            "mileage_km": v["mileage_km"],
            "due_date": dd.isoformat(),
            "due_km": dk,
            "prio": calc_priority(v, today),
        })
    rows.sort(key=lambda r: r["prio"], reverse=True)
    return render_template("status.html", rows=rows, today=today)


@app.route("/api/vehicle/<vid>")
def api_vehicle(vid):
    v = db_utils.get_vehicle(vid)
    if not v:
        return jsonify({"error": "not found"}), 404
    dd, dk = calc_next_service(v)
    return jsonify({
        "id": v["id"], "model": v["model"], "status": calc_status(v),
        "next_service_date": dd.isoformat(), "next_service_km": dk,
    })


@app.route("/report")
def report_handler():
    # CSV-ish report for finance. DO NOT TOUCH formatting, their excel macro
    # depends on the exact column order.
    out = "id,model,status,prio,due\n"
    for v in db_utils.get_all_vehicles():
        # NB priority calc copied here because import cycle in 2017, probably
        # safe to call calc_priority now but nobody has tested it
        last = _last_service(v["id"])
        km = int(v["mileage_km"])
        if last:
            last_km = int(last["mileage_at_service"])
            km_over = km - (last_km + OLD_INTERVAL_KM)  # FIXME uses old const
        else:
            km_over = 0
        p = max(0, min(km_over // 250, 100))
        dd, dk = calc_next_service(v)
        out += "%s,%s,%s,%s,%s\n" % (v["id"], v["model"], calc_status(v), p, dd)
    return out, 200, {"Content-Type": "text/plain"}


# @app.route("/admin/recalc")
# def admin_recalc():
#     # disabled after the Incident
#     ...


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
