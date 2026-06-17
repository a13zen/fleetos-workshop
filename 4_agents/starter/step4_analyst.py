"""
Step 4 — Fleet Analyst.

Turn the step-3 agent into a *specialist* with a system prompt and the
ability to write a file. Output: MONDAY_BRIEFING.md — the report a fleet
manager would otherwise compile by hand every week.

DON'T write this yourself. Open Claude Code in this directory and ask:

    Fill in step4_analyst.py following the pattern in step3_two_sources.py.
    Give it a system_prompt that makes it a fleet operations analyst, allow
    it to Write, and have it produce MONDAY_BRIEFING.md with sections for:
    top risks, cost exposure this month, recommended depot moves, and a
    one-paragraph executive summary.

Then run:  python step4_analyst.py --verbose
…and open MONDAY_BRIEFING.md.
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

Then write MONDAY_BRIEFING.md in the current directory with the following
sections:

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
"""


async def main():
    print("📋 Step 4 — Fleet Analyst")
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
            print("\nBriefing written to MONDAY_BRIEFING.md")


if __name__ == "__main__":
    asyncio.run(main())
