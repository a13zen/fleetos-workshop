"""
Stage 4 — Fleet Analyst specialist agent.

An Anthropic client with a "Fleet Analyst" system prompt.
Has access to:
  - FleetOS MCP (vehicle & maintenance data)
  - SQLite MCP (incidents, fuel_log, depot_capacity)
  - write_file(path, content) tool to produce output files

Runs the analyst and saves a MONDAY_BRIEFING.md with sections:
  - Top Risks
  - Cost Exposure
  - Recommended Actions
  - Executive Summary

Run:
    python step4_fleet_analyst.py [--verbose]

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
MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = """\
You are the Fleet Operations Analyst for a 12-vehicle commercial BMW fleet based in Germany.
Your job is to read the maintenance forecast (FleetOS API via mcp__fleetos__ tools) and the
operational database (incidents, fuel spend, depot capacity via mcp__sqlite__ tools), join
the data from both sources, and write a concise weekly briefing for the fleet manager.

Be specific and decisive: name vehicle IDs, quote figures, and recommend concrete actions
rather than listing observations. Write in plain prose and markdown tables — no JSON, no
bullet walls. When you reference money, use EUR (€).

Your output file must follow this exact structure:
# Monday Fleet Briefing

## Top Risks
(vehicles with overdue maintenance, high-severity incidents, or safety concerns — ranked by urgency)

## Cost Exposure
(fuel spend anomalies, upcoming service costs, deferred maintenance costs — with € figures)

## Recommended Actions
(specific actions: which vehicle, which depot, which week — use a markdown table)

## Executive Summary
(one paragraph, 3–5 sentences, written for a non-technical senior manager)
"""

USER_PROMPT = """\
Today is Monday. Read the fleet data from both the FleetOS API and the ops database,
then write the weekly fleet briefing to MONDAY_BRIEFING.md. Cover all four required
sections. Be thorough: check every vehicle's maintenance status, check for open incidents
(unresolved=0), and note depot bay availability for scheduling.
"""


# ---------------------------------------------------------------------------
# Minimal MCP stdio client (shared pattern with step3)
# ---------------------------------------------------------------------------

class MCPClient:
    """Minimal MCP stdio client — spawns server as subprocess over JSON-RPC."""

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
                               "clientInfo": {"name": "fleet-analyst", "version": "1.0"}}})
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
    """Return Anthropic tool defs and a name -> (client, original_name) map."""
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


# ---------------------------------------------------------------------------
# write_file tool
# ---------------------------------------------------------------------------

WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": (
        "Write text content to a file on disk. Use this to save the fleet briefing "
        "and any other output files. The path should be relative to the starter/ directory "
        "or an absolute path."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write (relative to starter/ dir or absolute).",
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


def handle_write_file(path: str, content: str) -> str:
    """Execute the write_file tool."""
    try:
        p = pathlib.Path(path)
        if not p.is_absolute():
            p = HERE / p
        resolved = p.resolve()
        if not any(resolved.is_relative_to(d.resolve()) for d in ALLOWED_DIRS):
            return f"Error: path {path!r} is outside allowed directories"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {resolved}"
    except Exception as e:
        return f"Error writing file: {e}"


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

def run_fleet_analyst(verbose: bool = False) -> str:
    """Run the Fleet Analyst agent and return its final response."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

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
                        preview = block.text[:200]
                        print(f"  Text: {preview}")
                    elif block.type == "tool_use":
                        args_str = str(block.input)[:100]
                        print(f"  -> {block.name}({args_str})")

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
                    )
                    if verbose:
                        print(f"  <- {result}")
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


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("Fleet Analyst Agent — Stage 4")
    print("=" * 50)
    print("Running analyst... will write MONDAY_BRIEFING.md when complete.\n")

    result = run_fleet_analyst(verbose=verbose)

    briefing_path = HERE / "MONDAY_BRIEFING.md"
    if briefing_path.exists():
        print(f"\nBriefing written to: {briefing_path}")
    else:
        print("\nNote: MONDAY_BRIEFING.md was not created (agent may not have called write_file).")

    if result:
        print("\nAgent final response:")
        print("=" * 50)
        print(result)


if __name__ == "__main__":
    main()
