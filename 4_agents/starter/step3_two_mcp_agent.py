"""
Stage 3 — Two-MCP agent using Bedrock bearer token auth via httpx.

Configures an agent with two MCP server configurations:
  1. FleetOS MCP (step2_fleetos_mcp.py) — vehicle & maintenance data from the REST API
  2. SQLite MCP (mcp-server-sqlite) — incidents, fuel log, depot capacity from fleet_ops.db

Creates and populates fleet_ops.db with realistic sample data if it doesn't exist,
then runs an agent that can answer questions requiring data from both sources.

Run:
    python step3_two_mcp_agent.py [--verbose] ["optional question"]

Requires:
    AWS_BEARER_TOKEN_BEDROCK env var
    AWS_REGION env var (optional, defaults to eu-central-1)
    FleetOS API running on localhost:8001 (uvicorn --app-dir .. fleetos_api.main:app --port 8001)
"""

import os
import sys
import sqlite3
import json
import httpx
import subprocess
from pathlib import Path
from typing import Any

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "fleet_ops.db"
MODEL = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"


def call_claude(messages, tools=None, system=None, max_tokens=4096):
    token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if not token:
        raise RuntimeError("AWS_BEARER_TOKEN_BEDROCK environment variable not set")
    region = os.environ.get("AWS_REGION", "eu-central-1")

    url = f"https://bedrock-runtime.{region}.amazonaws.com/model/{MODEL}/invoke"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if tools:
        body["tools"] = tools
    if system:
        body["system"] = system

    r = httpx.post(url, headers=headers, json=body, timeout=120.0)
    try:
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Bedrock API error {e.response.status_code}: {e.response.text}"
        ) from e
    return r.json()

DEFAULT_QUESTION = (
    "Which vehicles are flagged overdue or due soon by the FleetOS API "
    "AND have an unresolved high- or medium-severity incident in the ops "
    "database? For each one, tell me whether its home depot has a free "
    "workshop bay today. Rank by priority (highest first)."
)


def ensure_db():
    """Create and populate fleet_ops.db with sample data if it doesn't exist or is empty."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id  TEXT    NOT NULL,
            reported_at TEXT    NOT NULL,
            reported_by TEXT    NOT NULL,
            severity    TEXT    NOT NULL CHECK (severity IN ('low','medium','high')),
            category    TEXT    NOT NULL,
            description TEXT    NOT NULL,
            resolved    INTEGER NOT NULL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS fuel_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id  TEXT    NOT NULL,
            log_date    TEXT    NOT NULL,
            litres      REAL,
            kwh         REAL,
            cost_eur    REAL    NOT NULL,
            odometer_km INTEGER NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS depot_capacity (
            depot           TEXT    PRIMARY KEY,
            workshop_bays   INTEGER NOT NULL,
            bays_free_today INTEGER NOT NULL,
            region          TEXT    NOT NULL
        )
    """)

    # Only populate if tables are empty
    c.execute("SELECT COUNT(*) FROM incidents")
    if c.fetchone()[0] == 0:
        incidents = [
            ('VH-0017', '2026-04-02', 'S. Vogel',   'high',   'warning_light', 'Engine management light on since Monday, power feels reduced on inclines.', 0),
            ('VH-0017', '2026-03-18', 'S. Vogel',   'medium', 'noise',         'Intermittent rattle from rear suspension over cobbles.', 0),
            ('VH-0029', '2026-04-08', 'R. Schulz',  'high',   'handling',      'Pulls left under braking. Worse when loaded.', 0),
            ('VH-0126', '2026-03-30', 'K. Hofmann', 'medium', 'bodywork',      'Sliding door sticks, needs force to close fully.', 0),
            ('VH-0033', '2026-04-10', 'P. Neumann', 'low',    'noise',         'Squeak from dashboard area, cosmetic.', 0),
            ('VH-0023', '2026-04-05', 'I. Keller',  'medium', 'warning_light', 'Tyre pressure warning recurs after reset.', 0),
            ('VH-0064', '2026-02-14', 'L. Fischer', 'low',    'bodywork',      'Stone chip on windscreen, ~1cm, not in driver sightline.', 1),
            ('VH-0042', '2026-04-11', 'J. Brandt',  'low',    'electrical',    'USB charging port in cab intermittent.', 0),
            ('VH-0058', '2026-03-22', 'A. Lehmann', 'medium', 'electrical',    'Range estimate drops sharply below 20% — suspect battery cell imbalance.', 0),
            ('VH-0071', '2026-01-09', 'T. Roth',    'high',   'handling',      'ABS engaged unexpectedly on dry road.', 1),
            ('VH-0096', '2026-04-12', 'N. Hartmann','medium', 'noise',         'Whine from gearbox in 3rd gear under load.', 0),
            ('VH-0077', '2026-04-01', 'H. Winter',  'low',    'bodywork',      'Rear bumper scuff from loading dock.', 0),
        ]
        c.executemany(
            "INSERT INTO incidents (vehicle_id,reported_at,reported_by,severity,category,description,resolved) VALUES (?,?,?,?,?,?,?)",
            incidents,
        )

    c.execute("SELECT COUNT(*) FROM fuel_log")
    if c.fetchone()[0] == 0:
        fuel = [
            ('VH-0017', '2026-03-20', 72.4, None, 131.77, 154100),
            ('VH-0017', '2026-04-03', 75.1, None, 136.68, 155300),
            ('VH-0017', '2026-04-12', 78.9, None, 143.60, 156430),
            ('VH-0042', '2026-03-25', 58.0, None, 105.56, 82900),
            ('VH-0042', '2026-04-09', 56.3, None, 102.47, 84210),
            ('VH-0126', '2026-03-28', 80.2, None, 145.96, 140800),
            ('VH-0126', '2026-04-10', 81.5, None, 148.33, 142200),
            ('VH-0033', '2026-04-01', 63.7, None, 115.93, 130600),
            ('VH-0033', '2026-04-11', 62.9, None, 114.48, 131870),
            ('VH-0029', '2026-03-15', 49.8, None,  90.64, 176900),
            ('VH-0029', '2026-04-06', 68.2, None, 124.12, 178650),
            ('VH-0071', '2026-04-02', 41.0, None,  74.62,  96700),
            ('VH-0071', '2026-04-13', 40.3, None,  73.35,  97540),
            ('VH-0023', '2026-04-04', 47.5, None,  86.45, 118900),
            ('VH-0023', '2026-04-14', 46.9, None,  85.36, 119870),
            ('VH-0064', '2026-04-07', 44.1, None,  80.26,  62800),
            ('VH-0096', '2026-04-05', 70.3, None, 127.95,  71500),
            ('VH-0096', '2026-04-13', 69.8, None, 127.04,  72440),
            ('VH-0058', '2026-03-29', None, 61.0,  27.45,  17900),
            ('VH-0058', '2026-04-10', None, 64.0,  28.80,  18760),
            ('VH-0140', '2026-04-08', None, 58.0,  26.10,   9120),
            ('VH-0077', '2026-04-03', 38.6, None,  70.25,  54900),
            ('VH-0077', '2026-04-12', 37.9, None,  68.98,  55630),
            ('VH-0103', '2026-04-06', 39.4, None,  71.71,  40500),
            ('VH-0112', '2026-04-09', 55.0, None, 100.10,  27540),
        ]
        c.executemany(
            "INSERT INTO fuel_log (vehicle_id,log_date,litres,kwh,cost_eur,odometer_km) VALUES (?,?,?,?,?,?)",
            fuel,
        )

    c.execute("SELECT COUNT(*) FROM depot_capacity")
    if c.fetchone()[0] == 0:
        depots = [
            ('Hamburg Depot',                              4, 2, 'North'),
            ('Munich North Logistics Hub - Gate 14',       3, 0, 'South'),
            ('Berlin Tempelhof',                           2, 1, 'East'),
            ('Stuttgart Sued',                             3, 1, 'South'),
            ('Dingolfing Yard',                            6, 4, 'Central'),
            ('Frankfurt Service Centre',                   5, 3, 'Central'),
            ('Dingolfing Distribution Centre - Dock 3',   2, 0, 'Central'),
            ('Duesseldorf',                                2, 2, 'West'),
            ('Leipzig Service Centre',                     4, 1, 'East'),
            ('Koeln Innenstadt',                           1, 1, 'West'),
            ('Bremen Hafen',                               3, 0, 'North'),
            ('Nuernberg Ost',                              2, 2, 'South'),
            ('Dresden',                                    2, 1, 'East'),
            ('Hannover Messe - Hall 9',                    3, 2, 'North'),
            ('Dortmund',                                   2, 1, 'West'),
            ('Muenchen Service Centre',                    4, 3, 'South'),
            ('Essen',                                      2, 0, 'West'),
        ]
        c.executemany(
            "INSERT INTO depot_capacity (depot,workshop_bays,bays_free_today,region) VALUES (?,?,?,?)",
            depots,
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Minimal MCP stdio client helper
# ---------------------------------------------------------------------------

class MCPClient:
    """
    Minimal MCP stdio client.
    Spawns the MCP server as a subprocess and communicates via JSON-RPC over stdin/stdout.
    """

    def __init__(self, command: str, args: list[str]):
        self.command = command
        self.args = args
        self._proc: subprocess.Popen | None = None
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def start(self):
        self._proc = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        # Initialize
        self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05",
                               "capabilities": {},
                               "clientInfo": {"name": "step3-agent", "version": "1.0"}}})
        self._recv()
        # Send initialized notification
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def _send(self, obj: dict):
        line = json.dumps(obj) + "\n"
        self._proc.stdin.write(line)
        self._proc.stdin.flush()

    def _recv(self) -> dict:
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server process exited unexpectedly")
            try:
                msg = json.loads(line.strip())
            except json.JSONDecodeError as e:
                raise RuntimeError(f"MCP server sent invalid JSON: {line!r}") from e
            if "id" in msg:
                return msg

    def list_tools(self) -> list[dict]:
        req_id = self._next_id()
        self._send({"jsonrpc": "2.0", "id": req_id, "method": "tools/list", "params": {}})
        resp = self._recv()
        if "error" in resp:
            raise RuntimeError(f"tools/list failed: {resp['error']}")
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> Any:
        req_id = self._next_id()
        self._send({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})
        resp = self._recv()
        if "error" in resp:
            return f"MCP error: {resp['error'].get('message', str(resp['error']))}"
        content = resp.get("result", {}).get("content", [])
        # Extract text from content blocks
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts) if parts else str(content)

    def stop(self):
        if self._proc:
            self._proc.stdin.close()
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()


def build_tools_for_mcp(client: MCPClient, namespace: str) -> tuple[list[dict], dict]:
    """
    Query the MCP server for its tools and return:
    - Anthropic tool definitions (with namespaced names)
    - A mapping from namespaced tool name -> (client, original_name)
    """
    raw_tools = client.list_tools()
    anthropic_tools = []
    tool_map = {}

    for t in raw_tools:
        namespaced = f"mcp__{namespace}__{t['name']}"
        anthropic_tools.append({
            "name": namespaced,
            "description": t.get("description", ""),
            "input_schema": t.get("inputSchema", {"type": "object", "properties": {}}),
        })
        tool_map[namespaced] = (client, t["name"])

    return anthropic_tools, tool_map


def run_two_source_agent(question: str, verbose: bool = False) -> str:
    """
    Run an agent with access to both MCP servers (FleetOS API + SQLite ops DB).
    """
    # Ensure DB exists and has data
    ensure_db()

    fleetos_client = MCPClient(sys.executable, [str(HERE / "step2_fleetos_mcp.py")])
    sqlite_client = MCPClient("uvx", ["mcp-server-sqlite", "--db-path", str(DB_PATH)])

    fleetos_client.start()
    sqlite_client.start()

    try:
        fleetos_tools, fleetos_map = build_tools_for_mcp(fleetos_client, "fleetos")
        sqlite_tools, sqlite_map = build_tools_for_mcp(sqlite_client, "sqlite")

        all_tools = fleetos_tools + sqlite_tools
        tool_map = {**fleetos_map, **sqlite_map}

        messages = [
            {
                "role": "user",
                "content": (
                    "You can query the FleetOS maintenance API (tools prefixed mcp__fleetos__) "
                    "and the operational SQLite database (tools prefixed mcp__sqlite__). "
                    "The SQLite database has tables: incidents (vehicle_id, severity, category, "
                    "description, resolved), fuel_log (vehicle_id, litres, kwh, cost_eur, "
                    "odometer_km), and depot_capacity (depot, workshop_bays, bays_free_today, "
                    "region). Explore both data sources, then answer:\n\n" + question
                ),
            }
        ]

        MAX_TURNS = 20
        turn = 0
        response = None
        while True:
            turn += 1
            if turn > MAX_TURNS:
                print(f"Warning: agent exceeded {MAX_TURNS} turns, stopping")
                break
            if verbose:
                print(f"\n[Turn {turn}]")

            response = call_claude(messages, tools=all_tools, max_tokens=4096)

            stop_reason = response["stop_reason"]
            content = response["content"]

            if verbose:
                print(f"  Stop reason: {stop_reason}")
                for block in content:
                    if block.get("type") == "text":
                        print(f"  Text: {block['text'][:200]}")
                    elif block.get("type") == "tool_use":
                        print(f"  -> Tool: {block['name']}({block['input']})")

            messages.append({"role": "assistant", "content": content})

            if stop_reason == "max_tokens":
                print(f"Warning: response truncated at turn {turn}")
                break

            if stop_reason == "end_turn":
                for block in content:
                    if block.get("type") == "text":
                        return block["text"]
                return ""

            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    if block["name"] in tool_map:
                        mcp_client, original_name = tool_map[block["name"]]
                        result = mcp_client.call_tool(original_name, block["input"])
                    else:
                        result = f"Unknown tool: {block['name']}"

                    if verbose:
                        preview = result[:300] + "..." if len(result) > 300 else result
                        print(f"  <- {preview}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result,
                    })

            if not tool_results:
                break

            messages.append({"role": "user", "content": tool_results})

        # Fallback
        if response:
            for block in response["content"]:
                if block.get("type") == "text":
                    return block["text"]
        return ""

    finally:
        fleetos_client.stop()
        sqlite_client.stop()


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    argv_q = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    question = argv_q or DEFAULT_QUESTION

    print("Two-MCP Fleet Agent — Stage 3")
    print("=" * 50)
    print(f"Q: {question}\n")

    result = run_two_source_agent(question, verbose=verbose)
    print("\n" + "=" * 50)
    print(result)


if __name__ == "__main__":
    main()
