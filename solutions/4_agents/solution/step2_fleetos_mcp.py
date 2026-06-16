"""
Step 2 — Write your own MCP server.

This file is a *stub*. Your job is to fill in the TODOs so it becomes a
working MCP server that wraps the FleetOS REST API (the FastAPI service
from Challenge 2, running on http://localhost:8001).

Why this matters: any internal API in your company can be exposed to an
agent this way. Three tools, ~50 lines, and Claude can call your service.

Run standalone to smoke-test (it should sit waiting on stdin):
    python step2_fleetos_mcp.py

The agent in step3 will spawn this file as a subprocess and talk to it
over stdio — you never run it directly in normal use.

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
    Returns a list of dicts, each with id, make, model, location, mileage_km, status, next_service_date, and priority (0-100).
    Use this to get an overview of the fleet or to find vehicle IDs for follow-up calls.
    """
    r = httpx.get(f"{FLEETOS_API}/vehicles", timeout=10.0)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_maintenance(vehicle_id: str) -> dict:
    """
    Fetch the current maintenance details for a specific vehicle.
    Returns a dict with fields such as status, next_service_date, priority, and any outstanding issues.
    Use this after list_vehicles() to drill into a specific vehicle's maintenance needs.
    `vehicle_id` is the string ID from the fleet list.
    """
    r = httpx.get(f"{FLEETOS_API}/vehicles/{vehicle_id}/maintenance", timeout=10.0)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_service_history(vehicle_id: str) -> list[dict]:
    """
    Fetch the full service history for a specific vehicle.
    Returns a list of dicts, each representing a past service event with fields such as date, type, description, and cost.
    Use this to understand what work has already been done on a vehicle before scheduling new maintenance.
    `vehicle_id` is the string ID from the fleet list.
    """
    r = httpx.get(f"{FLEETOS_API}/vehicles/{vehicle_id}/history", timeout=10.0)
    r.raise_for_status()
    return r.json()



if __name__ == "__main__":
    mcp.run()
