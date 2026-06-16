"""
Step 5 — Multi-agent triage.

One orchestrator, three specialist subagents:

  - maintenance-planner : decides which vehicles get the free bays this week
  - cost-analyst        : quantifies € exposure of deferring each overdue vehicle
  - comms-drafter       : writes the driver-facing emails

Each subagent is an `AgentDefinition` (description + prompt + tools). The
orchestrator delegates with the `Task` tool and merges the results into
OPS_PLAN.md.

Run:  python step5_orchestrator.py --verbose
"""

import sys
import asyncio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition
from verbose import print_verbose

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "fleet_ops.db"

MCP_SERVERS = {
    "fleetos": {
        "command": sys.executable,
        "args": [str(HERE / "step2_fleetos_mcp.py")],
    },
    "sqlite": {
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", str(DB_PATH)],
    },
}

AGENTS = {
    "maintenance-planner": AgentDefinition(
        description="Allocates free workshop bays to the highest-risk vehicles",
        prompt=(
            "You are a maintenance scheduler. Pull the fleet status from the "
            "FleetOS API and depot capacity from the ops database, then produce "
            "a bay-by-bay plan for this week. Be specific: vehicle ID -> depot "
            "-> day. Only schedule into bays that are actually free."
        ),
        tools=["mcp__fleetos", "mcp__sqlite"],
    ),
    "cost-analyst": AgentDefinition(
        description="Quantifies the € exposure of deferring each overdue vehicle",
        prompt=(
            "You are a fleet cost analyst. For every overdue or due-soon "
            "vehicle, estimate the € cost of deferring its service by one more "
            "week — combine fuel-spend trend from the ops database with "
            "service history and priority from the FleetOS API. Return a table: "
            "vehicle ID | weekly deferral cost | one-line rationale."
        ),
        tools=["mcp__fleetos", "mcp__sqlite"],
    ),
    "comms-drafter": AgentDefinition(
        description="Writes driver-facing emails for vehicles being called in",
        prompt=(
            "You are the fleet operations coordinator. You will be given a list "
            "of vehicles being called in for service and their assigned slot. "
            "For each one, write a short, friendly email to the driver: subject "
            "line, two or three sentences, and the depot/date. Write all emails "
            "to a single file `DRIVER_EMAILS.md`."
        ),
        tools=["Write"],
    ),
}

ORCHESTRATOR_PROMPT = """\
You are coordinating this week's fleet operations plan.

1. Delegate to the `maintenance-planner` sub-agent to get the bay schedule.
2. Delegate to the `cost-analyst` sub-agent to get the deferral-cost table.
3. Delegate to the `comms-drafter` sub-agent — pass it the planner's
   schedule so it knows which vehicles and slots to write emails for.
4. Merge everything into `OPS_PLAN.md` with sections: Schedule,
   Deferral costs, and a note that driver emails are in `DRIVER_EMAILS.md`.

Use the Task tool for each delegation.
"""


async def main():
    print("🤝 Step 5 — Multi-Agent Orchestrator")
    print("=" * 50)

    async for message in query(
        prompt=ORCHESTRATOR_PROMPT,
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            mcp_servers=MCP_SERVERS,
            agents=AGENTS,
            allowed_tools=["Task", "Write"],
            permission_mode="bypassPermissions",
            cwd=str(HERE),
        ),
    ):
        print_verbose(message)
        if hasattr(message, "result"):
            print("\n" + "=" * 50)
            print(message.result)

    for f in ("OPS_PLAN.md", "DRIVER_EMAILS.md"):
        if (HERE / f).exists():
            print(f"✅ Wrote {HERE / f}")


if __name__ == "__main__":
    asyncio.run(main())
