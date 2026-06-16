"""
Step 3 — Two data sources, one agent.

The agent now has *two* MCP servers:
  - your `fleetos` server from step 2 (maintenance forecasts via the API)
  - an off-the-shelf SQLite server pointed at data/fleet_ops.db
    (driver incidents, fuel spend, depot capacity)

Neither system alone can answer "which overdue vehicles ALSO have an open
high-severity driver complaint, and does their depot have a free bay?" —
but an agent that can call both can.

Fill in the TODO, then run:
    python step3_two_sources.py --verbose
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

DEFAULT_QUESTION = (
    "Which vehicles are flagged overdue or maintenance by the FleetOS API "
    "AND have an unresolved high- or medium-severity incident in the ops "
    "database? For each one, tell me whether its home depot has a free "
    "workshop bay today. Rank by API priority."
)


async def main():
    print("🔌 Step 3 — Two-Source Fleet Agent")
    print("=" * 50)

    argv_q = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    question = argv_q or DEFAULT_QUESTION
    print(f"Q: {question}\n")

    async for message in query(
        prompt=(
            "You can query the FleetOS maintenance API (mcp__fleetos__*) and "
            "the operational SQLite database (mcp__sqlite__*). Explore both, "
            f"then answer:\n\n{question}"
        ),
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            mcp_servers=MCP_SERVERS,
            # Least-privilege: the agent can ONLY call these two services.
            # No Bash, no Write — DB rows and API responses are untrusted
            # input, so a prompt-injection in an incident description has
            # nowhere to go.
            allowed_tools=["mcp__fleetos", "mcp__sqlite"],
            permission_mode="bypassPermissions",
        ),
    ):
        print_verbose(message)
        if hasattr(message, "result"):
            print("\n" + "=" * 50)
            print(message.result)


if __name__ == "__main__":
    asyncio.run(main())
