"""
Step 1 — Minimal agent.

This is the smallest possible Agent SDK loop, pointed at local fleet data.
It already works — run it now to prove your environment is set up:

    python step1_minimal.py --verbose

Watch the cyan `→ Tool` lines: the agent decides for itself to read the
CSVs (we didn't tell it the filenames). The dim `── N turns · …s · $… ──`
footer at the end is your cost meter for the rest of the challenge.
"""

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from verbose import print_verbose


async def main():
    print("🚐 Step 1 — Minimal Fleet Agent")
    print("=" * 50)

    async for message in query(
        prompt=(
            "Look at the CSV files under ../fleetos_api/data/. "
            "Which five vehicles have the highest mileage, and which of "
            "those have no assigned driver? Answer in a short table."
        ),
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-5",
            allowed_tools=["Read", "Glob", "Bash"],
            permission_mode="bypassPermissions",
            setting_sources=["local"],
        ),
    ):
        print_verbose(message)
        if hasattr(message, "result"):
            print("\n" + message.result)


if __name__ == "__main__":
    asyncio.run(main())
