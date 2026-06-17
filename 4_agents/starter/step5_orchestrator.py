"""
Step 5 — Multi-agent triage.

One orchestrator, three specialist subagents:

  - maintenance-planner : decides which vehicles get the free bays this week
  - cost-analyst        : quantifies € exposure of deferring each overdue vehicle
  - comms-drafter       : writes the driver-facing emails

Each subagent is just an `AgentDefinition` (description + prompt + tools).
The orchestrator delegates with the `Task` tool and merges the results
into OPS_PLAN.md.

Open Claude Code and ask it to fill this in, using step4_analyst.py as
the reference pattern. Then compare the cost footer against step 4 — was
fanning out cheaper or dearer than one big agent?
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
        "command": sys.executable,
        "args": [str(HERE / "run_sqlite_mcp.py"), "--db-path", str(DB_PATH)],
    },
}

AGENTS = {
    "maintenance-planner": AgentDefinition(
        description=(
            "Allocates free workshop bays to the highest-risk vehicles. "
            "Checks which depots have capacity, ranks overdue vehicles by "
            "priority, and produces a bay-allocation schedule for the week."
        ),
        prompt=(
            "Query the FleetOS API (mcp__fleetos__*) for all overdue and "
            "critical-priority vehicles. Query the ops database "
            "(mcp__sqlite__*) for current depot bay availability. "
            "Match the highest-risk vehicles to depots with free bays. "
            "Return a structured allocation: vehicle ID, assigned depot, "
            "bay slot, and priority rank. If a depot is full, say so."
        ),
        tools=["mcp__fleetos", "mcp__sqlite"],
    ),
    "cost-analyst": AgentDefinition(
        description=(
            "Quantifies the € exposure of deferring maintenance on all "
            "overdue vehicles. Estimates cost per vehicle based on vehicle "
            "type, mileage, and days overdue."
        ),
        prompt=(
            "Query the FleetOS API (mcp__fleetos__*) for all overdue "
            "vehicles and their maintenance details. Query the ops database "
            "(mcp__sqlite__*) for any cost or fuel-spend data. "
            "For each overdue vehicle, estimate the financial exposure (€) "
            "of deferring maintenance by one more week, using mileage and "
            "vehicle type as proxies where exact costs are unavailable. "
            "Return a ranked table: vehicle ID, days overdue, estimated "
            "weekly deferral cost (€), and total exposure to date."
        ),
        tools=["mcp__fleetos", "mcp__sqlite"],
    ),
    "comms-drafter": AgentDefinition(
        description=(
            "Writes professional, concise driver-facing notification emails "
            "for vehicles that require immediate workshop attendance."
        ),
        prompt=(
            "You will be given a list of vehicles requiring immediate "
            "maintenance action, with their assigned depot and bay slot. "
            "Write a short, friendly but firm email to each driver notifying "
            "them of their required workshop appointment. Include: vehicle "
            "reference, depot address placeholder, appointment slot, and a "
            "brief reason why the service cannot be deferred. "
            "Keep each email under 150 words. Use a professional tone."
        ),
        tools=["Write"],
    ),
}

ORCHESTRATOR_PROMPT = """\
You are the fleet operations orchestrator. Coordinate three specialist
subagents to produce a complete weekly operations plan.

Steps:
1. Delegate to the `maintenance-planner` agent to get a bay-allocation
   schedule for the highest-risk vehicles.
2. Delegate to the `cost-analyst` agent to get the € exposure table for
   all overdue vehicles.
3. Using the allocation schedule from step 1 as context, delegate to the
   `comms-drafter` agent to write driver notification emails for every
   vehicle that has been allocated a bay.
4. Merge all three outputs into OPS_PLAN.md with clear section headings:
   - Bay Allocation Schedule
   - Cost Exposure Summary
   - Driver Notifications (the email texts)
   - Actions Required (a bullet-point checklist for the ops manager)

Write the final OPS_PLAN.md file using the Write tool.
"""


async def main():
    print("🤖 Step 5 — Multi-Agent Fleet Triage")
    print("=" * 50)

    async for message in query(
        prompt=ORCHESTRATOR_PROMPT,
        options=ClaudeAgentOptions(
            model="eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            mcp_servers=MCP_SERVERS,
            allowed_tools=["Task", "Write", "mcp__fleetos", "mcp__sqlite"],
            agents=AGENTS,
            permission_mode="bypassPermissions",
            setting_sources=["local"],
        ),
    ):
        print_verbose(message)
        if hasattr(message, "result"):
            print("\n" + "=" * 50)
            print(message.result)
            print("\nOperations plan written to OPS_PLAN.md")


if __name__ == "__main__":
    asyncio.run(main())
