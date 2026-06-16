"""
Step 4 — Fleet Analyst.

The step-3 agent, given a role and a pen. A system prompt turns the
generalist into a Fleet Operations Analyst, and adding `Write` to the
allowed tools lets it produce MONDAY_BRIEFING.md — the report a fleet
manager would otherwise compile by hand.

Run:  python step4_analyst.py --verbose
…then open MONDAY_BRIEFING.md.
"""

import sys
import asyncio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions
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

SYSTEM_PROMPT = """\
You are the Fleet Operations Analyst for a 12-vehicle commercial fleet.
Your job is to read the maintenance forecast (FleetOS API) and the
operational database (incidents, fuel spend, depot capacity), join them,
and write a concise weekly briefing for the fleet manager.

Be specific and decisive: name vehicle IDs, quote figures, and recommend
actions rather than listing observations. Write in plain prose and
markdown tables — no JSON, no bullet walls.
"""

USER_PROMPT = """\
Produce this week's ops briefing as `MONDAY_BRIEFING.md` in the current
directory. Structure it with these sections:

1. **Executive summary** — three or four sentences, the headline.
2. **Top risks** — vehicles to act on this week, with the *why*
   (overdue + open incident, fuel anomaly, etc).
3. **Cost exposure this month** — fuel spend, projected maintenance.
4. **Recommended depot moves** — which vehicle into which free bay.

Use the FleetOS tools (mcp__fleetos__*) and the SQLite tools
(mcp__sqlite__*) to gather everything you need first, then write the file.

Also write a machine-readable `../dashboard/briefing.json` — an array of
objects with keys `vehicle_id`, `risk` (low/medium/high), `action`, and
`why` (one sentence). Only include vehicles that need action this week.
"""


async def main():
    print("📝 Step 4 — Fleet Analyst")
    print("=" * 50)

    async for message in query(
        prompt=USER_PROMPT,
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            system_prompt=SYSTEM_PROMPT,
            mcp_servers=MCP_SERVERS,
            allowed_tools=["mcp__fleetos", "mcp__sqlite", "Write"],
            permission_mode="bypassPermissions",
            cwd=str(HERE),
        ),
    ):
        print_verbose(message)
        if hasattr(message, "result"):
            print("\n" + "=" * 50)
            print(message.result)

    for f in (HERE / "MONDAY_BRIEFING.md", HERE.parent / "dashboard" / "briefing.json"):
        if f.exists():
            print(f"✅ Wrote {f}")


if __name__ == "__main__":
    asyncio.run(main())
