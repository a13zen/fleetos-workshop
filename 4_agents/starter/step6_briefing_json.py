"""
Stage 6 — Fleet Analyst with JSON output for the dashboard.

Extends Stage 4: runs the Fleet Analyst agent and produces two outputs:
  1. MONDAY_BRIEFING.md — the human-readable weekly briefing (same as step 4)
  2. briefing.json — machine-readable array of {vehicle_id, risk, action, why}
     written to ../dashboard/briefing.json so the dashboard can serve it

The JSON format feeds the dashboard's "Agent Briefing" card.
Each entry: {"vehicle_id": str, "risk": "low"|"medium"|"high", "action": str, "why": str}

Run:
    python step6_briefing_json.py [--verbose]

Then serve the dashboard:
    cd ../dashboard && python3 -m http.server 8000

Requires:
    ANTHROPIC_API_KEY env var
    FleetOS API running on localhost:8001
"""

import os
import sys
import json
import subprocess
import pathlib
from pathlib import Path
from typing import Any
import anthropic

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "fleet_ops.db"
DASHBOARD_DIR = HERE.parent / "dashboard"
MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = """\
You are the Fleet Operations Analyst for a 12-vehicle commercial BMW fleet based in Germany.
Your job is to read the maintenance forecast (FleetOS API via mcp__fleetos__ tools) and the
operational database (incidents, fuel spend, depot capacity via mcp__sqlite__ tools), join
the data from both sources, and produce two output files for the fleet manager.

Be specific and decisive: name vehicle IDs, quote figures, and recommend concrete actions.
Write in plain prose and markdown tables. When you reference money, use EUR (€).

IMPORTANT: You must produce BOTH output files by calling write_file twice:

1. MONDAY_BRIEFING.md — a full markdown briefing with these sections:
   # Monday Fleet Briefing
   ## Top Risks
   ## Cost Exposure
   ## Recommended Actions
   ## Executive Summary

2. briefing.json — a JSON array (only vehicles needing action this week).
   Each element must be exactly: {"vehicle_id": "VH-XXXX", "risk": "low|medium|high", "action": "...", "why": "..."}
   - risk: "high" = overdue/safety risk, "medium" = due_soon/open incident, "low" = minor issue
   - action: short imperative (under 10 words), e.g. "Book workshop slot this week"
   - why: one sentence explaining the reason

Write briefing.json to: ../dashboard/briefing.json
Write MONDAY_BRIEFING.md to: MONDAY_BRIEFING.md
"""

USER_PROMPT = """\
Today is Monday. Read the fleet data from both the FleetOS API and the ops database.

Steps:
1. Call mcp__fleetos__list_vehicles to get all vehicles and their status/priority
2. Query the SQLite database for unresolved incidents:
   SELECT vehicle_id, severity, category, description FROM incidents WHERE resolved=0
3. Query depot capacity:
   SELECT * FROM depot_capacity
4. Query recent fuel costs:
   SELECT vehicle_id, SUM(cost_eur) as total_cost, MAX(odometer_km)-MIN(odometer_km) as km
   FROM fuel_log GROUP BY vehicle_id
5. Write MONDAY_BRIEFING.md with all four sections
6. Write ../dashboard/briefing.json with the structured risk data for the dashboard

Only include vehicles in briefing.json that need action this week (status overdue/due_soon
or unresolved medium/high incidents). Exclude vehicles with only low-severity resolved issues.
"""


# ---------------------------------------------------------------------------
# Minimal MCP stdio client (same pattern as steps 3-5)
# ---------------------------------------------------------------------------

class MCPClient:
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
        self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05",
                               "capabilities": {},
                               "clientInfo": {"name": "briefing-json-agent", "version": "1.0"}}})
        self._recv()
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def _send(self, obj: dict):
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def _recv(self) -> dict:
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server process exited unexpectedly")
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"MCP server sent invalid JSON: {line!r}") from e

    def list_tools(self) -> list[dict]:
        req_id = self._next_id()
        self._send({"jsonrpc": "2.0", "id": req_id, "method": "tools/list", "params": {}})
        return self._recv().get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> str:
        req_id = self._next_id()
        self._send({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})
        resp = self._recv()
        content = resp.get("result", {}).get("content", [])
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
            self._proc.wait(timeout=5)


def build_tools_for_mcp(client: MCPClient, namespace: str) -> tuple[list[dict], dict]:
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


WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": (
        "Write text content to a file on disk. "
        "Use path 'MONDAY_BRIEFING.md' for the markdown briefing. "
        "Use path '../dashboard/briefing.json' for the JSON dashboard output."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path relative to starter/ directory or absolute.",
            },
            "content": {
                "type": "string",
                "description": "Full text content to write to the file.",
            },
        },
        "required": ["path", "content"],
    },
}


ALLOWED_DIRS = [HERE, HERE.parent / "dashboard"]


def handle_write_file(path: str, content: str, verbose: bool = False) -> str:
    try:
        p = pathlib.Path(path)
        if not p.is_absolute():
            p = HERE / p
        resolved = p.resolve()
        if not any(resolved.is_relative_to(d.resolve()) for d in ALLOWED_DIRS):
            return f"Error: path {path!r} is outside allowed directories"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")

        # Validate JSON if this is a .json file
        if resolved.suffix == ".json":
            try:
                parsed = json.loads(content)
                if verbose:
                    print(f"  [write_file] Valid JSON: {len(parsed)} entries written to {resolved}")
            except json.JSONDecodeError as e:
                return f"Warning: wrote file but JSON is invalid: {e}"

        return f"Successfully wrote {len(content)} characters to {resolved}"
    except Exception as e:
        return f"Error writing file: {e}"


def run_briefing_agent(verbose: bool = False) -> str:
    """Run the briefing agent that produces both MONDAY_BRIEFING.md and briefing.json."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Ensure dashboard directory exists
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    fleetos_client = MCPClient(sys.executable, [str(HERE / "step2_fleetos_mcp.py")])
    sqlite_client = MCPClient("uvx", ["mcp-server-sqlite", "--db-path", str(DB_PATH)])

    fleetos_client.start()
    sqlite_client.start()

    try:
        fleetos_tools, fleetos_map = build_tools_for_mcp(fleetos_client, "fleetos")
        sqlite_tools, sqlite_map = build_tools_for_mcp(sqlite_client, "sqlite")

        all_tools = fleetos_tools + sqlite_tools + [WRITE_FILE_TOOL]
        tool_map: dict[str, Any] = {**fleetos_map, **sqlite_map}

        client = anthropic.Anthropic(api_key=api_key)
        messages = [{"role": "user", "content": USER_PROMPT}]

        MAX_TURNS = 20
        turn = 0
        while True:
            turn += 1
            if turn > MAX_TURNS:
                print(f"Warning: agent exceeded {MAX_TURNS} turns, stopping")
                break
            if verbose:
                print(f"\n[Turn {turn}]")

            response = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                tools=all_tools,
                messages=messages,
            )

            if verbose:
                print(f"  Stop reason: {response.stop_reason}")
                for block in response.content:
                    if hasattr(block, "text"):
                        print(f"  Text: {block.text[:200]}")
                    elif block.type == "tool_use":
                        if block.name == "write_file":
                            path = block.input.get("path", "")
                            content_len = len(block.input.get("content", ""))
                            print(f"  -> write_file({path}, {content_len} chars)")
                        else:
                            print(f"  -> {block.name}({str(block.input)[:80]})")

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "max_tokens":
                print(f"Warning: response truncated at turn {turn}")
                break

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return "Briefing complete."

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if block.name == "write_file":
                    result = handle_write_file(
                        block.input.get("path", "output.txt"),
                        block.input.get("content", ""),
                        verbose=verbose,
                    )
                elif block.name in tool_map:
                    mcp_client, original_name = tool_map[block.name]
                    result = mcp_client.call_tool(original_name, block.input)
                    if verbose:
                        preview = result[:200] + "..." if len(result) > 200 else result
                        print(f"  <- {preview}")
                else:
                    result = f"Unknown tool: {block.name}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            if not tool_results:
                break

            messages.append({"role": "user", "content": tool_results})

        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "Agent loop ended."

    finally:
        fleetos_client.stop()
        sqlite_client.stop()


def _check_outputs():
    """Report on generated output files."""
    briefing_md = HERE / "MONDAY_BRIEFING.md"
    briefing_json = DASHBOARD_DIR / "briefing.json"

    print("\n--- Output files ---")
    if briefing_md.exists():
        size = briefing_md.stat().st_size
        print(f"  MONDAY_BRIEFING.md: {size} bytes — {briefing_md}")
    else:
        print(f"  MONDAY_BRIEFING.md: NOT CREATED")

    if briefing_json.exists():
        size = briefing_json.stat().st_size
        print(f"  briefing.json:      {size} bytes — {briefing_json}")
        try:
            data = json.loads(briefing_json.read_text())
            print(f"  briefing.json contains {len(data)} vehicle entries:")
            for entry in data:
                vid = entry.get("vehicle_id", "?")
                risk = entry.get("risk", "?")
                action = entry.get("action", "?")
                print(f"    {vid} [{risk}]: {action}")
        except Exception as e:
            print(f"  briefing.json parse error: {e}")
    else:
        print(f"  briefing.json:      NOT CREATED (needed for dashboard at {briefing_json})")

    print("\nTo view the dashboard:")
    print(f"  cd {DASHBOARD_DIR} && python3 -m http.server 8000")
    print("  Open http://localhost:8000")


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("Fleet Briefing JSON Agent — Stage 6")
    print("="*50)
    print("Running analyst... will write MONDAY_BRIEFING.md and briefing.json\n")

    result = run_briefing_agent(verbose=verbose)

    if result and result not in ("Briefing complete.", "Agent loop ended."):
        print("\nAgent final response:")
        print("="*50)
        print(result)

    _check_outputs()


if __name__ == "__main__":
    main()
