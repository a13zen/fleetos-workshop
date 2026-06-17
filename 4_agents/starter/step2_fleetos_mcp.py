"""
Stage 2 — MCP server wrapping the FleetOS REST API.

Exposes three tools to MCP clients (agents):
  - list_vehicles()         → GET /vehicles
  - get_maintenance(id)     → GET /vehicles/{id}/maintenance
  - get_service_history(id) → GET /vehicles/{id}/history

Each tool makes an HTTP request to the FleetOS FastAPI running on
http://localhost:8001. The server communicates over stdio (standard MCP
transport) so it can be spawned as a subprocess by an agent.

Run in isolation to smoke-test (it will wait on stdin):
    python step2_fleetos_mcp.py

Docs: https://modelcontextprotocol.io/quickstart/server
"""

import os
import httpx
from mcp.server.fastmcp import FastMCP

FLEETOS_API = os.environ.get("FLEETOS_API", "http://localhost:8001")

mcp = FastMCP("fleetos")


@mcp.tool()
def list_vehicles() -> list[dict]:
    """
    Fetch all vehicles in the fleet with their current maintenance status and priority.
    Returns a list of dicts, each with: id, make, model, year, vehicle_class, location,
    mileage_km, assigned_driver, status, last_service_date, next_service_date, and
    priority (0-100, higher means more urgent).
    Use this to get an overview of the entire fleet or to find vehicle IDs for follow-up
    calls to get_maintenance or get_service_history.
    """
    r = httpx.get(f"{FLEETOS_API}/vehicles", timeout=10.0)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_maintenance(vehicle_id: str) -> dict:
    """
    Fetch the maintenance forecast for a single vehicle.
    Returns a dict with: status (ok/due_soon/overdue), last_service_date,
    next_service_date, next_service_km, and priority (0-100).
    Use this when you need to assess the maintenance urgency or upcoming service
    needs for a specific vehicle.
    Args: vehicle_id - the vehicle's ID string (e.g. 'VH-0042'), as returned by
    list_vehicles.
    """
    r = httpx.get(f"{FLEETOS_API}/vehicles/{vehicle_id}/maintenance", timeout=10.0)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_service_history(vehicle_id: str) -> list[dict]:
    """
    Fetch the full workshop service history for a single vehicle, most recent first.
    Returns a list of service records, each with: service_date, mileage_at_service,
    work_performed, and cost_eur.
    Use this when you need to understand past maintenance patterns, calculate total
    service costs, or identify recurring issues for a specific vehicle.
    Args: vehicle_id - the vehicle's ID string (e.g. 'VH-0042'), as returned by
    list_vehicles.
    """
    r = httpx.get(f"{FLEETOS_API}/vehicles/{vehicle_id}/history", timeout=10.0)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    mcp.run()
