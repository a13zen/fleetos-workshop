"""
Step 2 — Write your own MCP server.

This file is a *stub*. Your job is to fill in the TODOs so it becomes a
working MCP server that wraps the FleetOS REST API (the FastAPI service
bundled in ../fleetos_api/, running on http://localhost:8001).

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


# TODO: add a tool that wraps GET /vehicles/{vehicle_id}/maintenance
#   - name it `get_maintenance(vehicle_id: str) -> dict`
#   - follow the docstring pattern above: what it does, what it returns, when to use it, and what the argument is


# TODO: add a tool that wraps GET /vehicles/{vehicle_id}/history
#   - name it `get_service_history(vehicle_id: str) -> list[dict]`
#   - follow the same docstring pattern


if __name__ == "__main__":
    mcp.run()
