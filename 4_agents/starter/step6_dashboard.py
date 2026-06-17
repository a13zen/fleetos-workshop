"""
Step 6 — Dashboard Feed.

Extends step 4 (Fleet Analyst) with an additional output: a JSON file
consumed by the web dashboard. The agent writes:

  - MONDAY_BRIEFING.md  (same as step 4)
  - ../dashboard/briefing.json  (array of {vehicle_id, risk, action, why}
    for every vehicle needing attention this week)

Run:  python step6_dashboard.py --verbose
Then open the dashboard to see the briefing cards populated automatically.
"""

import sys
import os
import asyncio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions
from verbose import print_verbose


_BEDROCK_KEYS = [
    "CLAUDE_CODE_USE_BEDROCK", "AWS_BEARER_TOKEN_BEDROCK",
    "AWS_REGION", "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
]


def bedrock_env() -> dict:
    return {k: v for k, v in os.environ.items() if k in _BEDROCK_KEYS and v}

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

SYSTEM_PROMPT = """\
You are a senior fleet operations analyst. Your job is to synthesise data
from two sources — the FleetOS maintenance API and the operational SQLite
database — and produce clear, actionable management reports.

Guidelines:
- Always cross-reference both data sources before drawing conclusions.
- Quantify risk and cost exposure where possible.
- Be concise: managers read on mobile; bullet points beat paragraphs.
- When recommending depot moves, consider bay availability and travel distance.
- Flag any data gaps or anomalies you encounter.
"""

USER_PROMPT = """\
Read the FleetOS maintenance API (mcp__fleetos__*) and the operational
SQLite database (mcp__sqlite__*) to gather the full picture of the fleet
right now.

Then produce TWO output files:

--- File 1: MONDAY_BRIEFING.md ---
Write MONDAY_BRIEFING.md in the current directory with the following sections:

1. **Top Risks** — vehicles that are overdue or flagged critical, ranked by
   priority. Include vehicle ID, current status, and days overdue.

2. **Cost Exposure This Month** — estimated € cost of deferring maintenance
   on all overdue vehicles. Derive from mileage, vehicle type, and any cost
   data in the ops database.

3. **Recommended Depot Moves** — which vehicles should be redirected to a
   different depot to take advantage of free workshop bays? Include the
   from/to depot and the reason.

4. **Executive Summary** — one paragraph suitable for a Monday morning
   briefing email to the operations director.

Use markdown formatting. Include a timestamp at the top of the file.

--- File 2: ../dashboard/briefing.json ---
Write ../dashboard/briefing.json containing a JSON array of objects for
every vehicle that needs attention this week. Each object must have exactly
these four fields:
  - vehicle_id  : string, the vehicle identifier
  - risk        : string, one of "critical", "high", "medium", or "low"
  - action      : string, short imperative describing what must be done
                  (e.g. "Book workshop slot", "Redirect to Depot B")
  - why         : string, one sentence explaining the reason

Only include vehicles genuinely needing action this week — do not pad the
list. Ensure the JSON is valid and pretty-printed with 2-space indentation.
"""


async def main():
    print("📊 Step 6 — Fleet Analyst + Dashboard Feed")
    print("=" * 50)

    async for message in query(
        prompt=USER_PROMPT,
        options=ClaudeAgentOptions(
            model="eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            system_prompt=SYSTEM_PROMPT,
            mcp_servers=MCP_SERVERS,
            allowed_tools=["mcp__fleetos", "mcp__sqlite", "Write"],
            permission_mode="bypassPermissions",
            setting_sources=["local"],
            env=bedrock_env(),
        ),
    ):
        print_verbose(message)
        if hasattr(message, "result"):
            print("\n" + "=" * 50)
            print(message.result)
            print("\nFiles written:")
            print("  - MONDAY_BRIEFING.md")
            print("  - ../dashboard/briefing.json")


if __name__ == "__main__":
    asyncio.run(main())
