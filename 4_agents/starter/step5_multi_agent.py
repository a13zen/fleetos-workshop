"""
Stage 5 — Multi-agent orchestration using the Anthropic SDK directly.

Orchestrator agent that spawns 3 specialist sub-agents sequentially:
  1. maintenance-planner — allocates depot bays to highest-risk vehicles
  2. cost-analyst        — quantifies EUR exposure of deferring overdue vehicles
  3. comms-drafter       — writes driver-facing emails for vehicles being called in

Each sub-agent gets a targeted system prompt and a constrained set of tools.
The orchestrator merges all outputs into OPS_PLAN.md.

Run:
    python step5_multi_agent.py [--verbose]

Requires:
    ANTHROPIC_API_KEY env var
    FleetOS API running on localhost:8001
"""

import os
import sys
import json
import subprocess
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
MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Minimal MCP stdio client (same pattern as steps 3 & 4)
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
                               "clientInfo": {"name": "multi-agent-orch", "version": "1.0"}}})
        self._recv()
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def _send(self, obj: dict):
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def _recv(self) -> dict:
        line = self._proc.stdout.readline()
        return json.loads(line.strip()) if line.strip() else {}

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


WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": "Write text content to a file on disk.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path (relative to starter/ or absolute)."},
            "content": {"type": "string", "description": "Text content to write."},
        },
        "required": ["path", "content"],
    },
}


def handle_write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        if not p.is_absolute():
            p = HERE / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to {p}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Sub-agent runner
# ---------------------------------------------------------------------------

def run_sub_agent(
    name: str,
    system_prompt: str,
    user_prompt: str,
    tools: list[dict],
    tool_map: dict[str, Any],
    verbose: bool = False,
) -> str:
    """
    Run a specialist sub-agent with a given system prompt and tool set.
    Returns the final text response.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": user_prompt}]

    if verbose:
        print(f"\n[{name}] Starting sub-agent")

    turn = 0
    while True:
        turn += 1
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tools if tools else anthropic.NOT_GIVEN,
            messages=messages,
        )

        if verbose:
            print(f"  [{name}] Turn {turn}, stop={response.stop_reason}")
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [{name}] -> {block.name}({str(block.input)[:80]})")

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "write_file":
                result = handle_write_file(
                    block.input.get("path", "output.txt"),
                    block.input.get("content", ""),
                )
            elif block.name in tool_map:
                mcp_client, original_name = tool_map[block.name]
                result = mcp_client.call_tool(original_name, block.input)
            else:
                result = f"Unknown tool: {block.name}"

            if verbose:
                preview = result[:200] + "..." if len(result) > 200 else result
                print(f"  [{name}] <- {preview}")

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
    return ""


# ---------------------------------------------------------------------------
# Specialist sub-agent definitions
# ---------------------------------------------------------------------------

AGENTS = {
    "maintenance-planner": {
        "description": "Allocates free workshop bays to highest-risk vehicles this week",
        "system_prompt": (
            "You are a maintenance scheduler for a commercial BMW fleet in Germany. "
            "Your job: given the fleet maintenance status (from FleetOS API) and depot "
            "workshop bay availability (from the SQLite ops database), produce a concrete "
            "bay-allocation plan for this week. Be specific: for each vehicle that needs "
            "service, state the vehicle ID, its current depot, its maintenance status and "
            "priority score, whether its home depot has a free bay, and your recommended "
            "action (book at home depot / transfer to nearest depot with capacity / defer). "
            "Present your plan as a markdown table. Do not recommend deferring high-priority vehicles."
        ),
        "user_prompt": (
            "Query the FleetOS API to get all vehicles and their maintenance status. "
            "Then query the SQLite database for depot_capacity (SELECT * FROM depot_capacity). "
            "Match each vehicle's location to its depot capacity. "
            "Produce a bay-allocation plan for this week covering all vehicles with "
            "status 'overdue' or 'due_soon'. Output your plan as a markdown table with columns: "
            "Vehicle ID | Location/Depot | Status | Priority | Free Bays | Recommended Action."
        ),
        "tool_namespaces": ["fleetos", "sqlite"],
    },
    "cost-analyst": {
        "description": "Quantifies EUR exposure of deferring overdue vehicles another week",
        "system_prompt": (
            "You are a fleet cost analyst. Your job: quantify the financial exposure of "
            "deferring maintenance on overdue or high-risk vehicles for another week. "
            "Use service history cost data and fuel log anomalies to build your estimate. "
            "Be specific with numbers: quote actual € figures from the data, calculate "
            "fuel cost per km where possible, and flag vehicles with rising costs. "
            "Consider both direct service costs (rising if deferred) and indirect costs "
            "(excess fuel consumption, potential breakdowns). "
            "Present a ranked table of cost exposure by vehicle."
        ),
        "user_prompt": (
            "Query the FleetOS API for vehicle maintenance status and service history. "
            "Query the SQLite database for: "
            "SELECT vehicle_id, SUM(cost_eur) as total_fuel_cost, "
            "MAX(odometer_km)-MIN(odometer_km) as km_driven FROM fuel_log GROUP BY vehicle_id; "
            "Also check for unresolved incidents: "
            "SELECT vehicle_id, severity, category, description FROM incidents WHERE resolved=0; "
            "Calculate fuel cost per 100km for each vehicle. Flag anomalies. "
            "Estimate deferral cost exposure (€) for each overdue vehicle. "
            "Present results as a markdown table: "
            "Vehicle ID | Status | Fuel €/100km | Deferred Service Est. Cost | Risk."
        ),
        "tool_namespaces": ["fleetos", "sqlite"],
    },
    "comms-drafter": {
        "description": "Writes driver-facing emails for vehicles being called in for service",
        "system_prompt": (
            "You are the fleet communications officer. Your job: write professional, "
            "friendly driver-facing email notifications for vehicles that need to be "
            "called in for workshop service this week. "
            "Tone: professional but not alarming. Be specific about what is needed and why. "
            "Each email should include: subject line, greeting, reason for service call, "
            "what the driver needs to do (drop off date/location), and sign-off. "
            "Write in English. Keep each email under 150 words."
        ),
        "user_prompt": (
            "Based on the following vehicle service requirements, write driver notification "
            "emails for vehicles being called in this week:\n\n"
            "High priority (immediate call-in):\n"
            "- VH-0017 (BMW X5, Munich North Logistics Hub): Engine management warning light, "
            "overdue service, priority 95. Driver: S. Vogel\n"
            "- VH-0029 (BMW X1, Bremen Hafen): Pulling left under braking, overdue service, "
            "priority 90. Driver: R. Schulz\n\n"
            "Medium priority (this week):\n"
            "- VH-0009 (BMW 5 Series Touring, Dingolfing Yard): Overdue service, "
            "no assigned driver — send to depot manager\n"
            "- VH-0050 (BMW 1 Series, Dingolfing Yard): Overdue service, "
            "no assigned driver — send to depot manager\n"
            "- VH-0126 (BMW X5, Dingolfing Distribution Centre): Due soon, "
            "sticking door reported. Driver: K. Hofmann\n\n"
            "Write one email per vehicle. Format clearly with --- between emails."
        ),
        "tool_namespaces": [],  # comms drafter only needs write_file
    },
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_orchestrator(verbose: bool = False):
    """
    Orchestrator: runs each specialist sub-agent sequentially and merges
    their outputs into OPS_PLAN.md.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Start MCP servers (shared across sub-agents that need them)
    fleetos_client = MCPClient(sys.executable, [str(HERE / "step2_fleetos_mcp.py")])
    sqlite_client = MCPClient("uvx", ["mcp-server-sqlite", "--db-path", str(DB_PATH)])

    fleetos_client.start()
    sqlite_client.start()

    try:
        fleetos_tools, fleetos_map = build_tools_for_mcp(fleetos_client, "fleetos")
        sqlite_tools, sqlite_map = build_tools_for_mcp(sqlite_client, "sqlite")
        all_data_tools = fleetos_tools + sqlite_tools
        all_data_map: dict[str, Any] = {**fleetos_map, **sqlite_map}

        results: dict[str, str] = {}

        # Run each specialist sub-agent
        for agent_name, agent_def in AGENTS.items():
            print(f"\n{'='*50}")
            print(f"Running sub-agent: {agent_name}")
            print(f"  {agent_def['description']}")
            print('='*50)

            namespaces = agent_def["tool_namespaces"]

            # Build tool list for this agent
            agent_tools = []
            agent_map: dict[str, Any] = {}

            if "fleetos" in namespaces:
                agent_tools.extend(fleetos_tools)
                agent_map.update(fleetos_map)
            if "sqlite" in namespaces:
                agent_tools.extend(sqlite_tools)
                agent_map.update(sqlite_map)

            # All agents can write files
            agent_tools.append(WRITE_FILE_TOOL)

            result = run_sub_agent(
                name=agent_name,
                system_prompt=agent_def["system_prompt"],
                user_prompt=agent_def["user_prompt"],
                tools=agent_tools,
                tool_map=agent_map,
                verbose=verbose,
            )
            results[agent_name] = result
            if verbose:
                print(f"\n[{agent_name}] Output preview: {result[:300]}...")

        # Orchestrator merges all sub-agent outputs into OPS_PLAN.md
        print("\n" + "="*50)
        print("Orchestrator: merging outputs into OPS_PLAN.md")
        print("="*50)

        ops_plan = f"""# Fleet Operations Plan — Week of {_today()}

*Generated by multi-agent orchestration: maintenance-planner + cost-analyst + comms-drafter*

---

## Bay Allocation Plan
*(maintenance-planner sub-agent)*

{results.get('maintenance-planner', '_No output from maintenance-planner_')}

---

## Cost Exposure Analysis
*(cost-analyst sub-agent)*

{results.get('cost-analyst', '_No output from cost-analyst_')}

---

## Driver Communications
*(comms-drafter sub-agent)*

{results.get('comms-drafter', '_No output from comms-drafter_')}

---

*End of Operations Plan*
"""

        ops_path = HERE / "OPS_PLAN.md"
        ops_path.write_text(ops_plan, encoding="utf-8")
        print(f"\nOPS_PLAN.md written to: {ops_path}")
        return ops_plan

    finally:
        fleetos_client.stop()
        sqlite_client.stop()


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("Multi-Agent Fleet Orchestrator — Stage 5")
    print("="*50)
    print("Spawning 3 specialist sub-agents sequentially:")
    print("  1. maintenance-planner")
    print("  2. cost-analyst")
    print("  3. comms-drafter")
    print("="*50)

    run_orchestrator(verbose=verbose)

    print("\nDone. OPS_PLAN.md has been written.")


if __name__ == "__main__":
    main()
