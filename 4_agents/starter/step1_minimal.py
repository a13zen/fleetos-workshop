"""
Step 1 — Minimal agent.

This is the smallest possible Agent SDK loop, pointed at local fleet data.
It already works — run it now to prove your environment is set up:

    python step1_minimal.py --verbose

Watch the cyan `→ Tool` lines: the agent decides for itself to read the
CSVs (we didn't tell it the filenames). The dim `── N turns · …s · $… ──`
footer at the end is your cost meter for the rest of the challenge.
"""

import os
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from verbose import print_verbose

_BEDROCK_KEYS = [
    "CLAUDE_CODE_USE_BEDROCK", "AWS_BEARER_TOKEN_BEDROCK",
    "AWS_REGION", "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
]


def bedrock_env() -> dict:
    return {k: v for k, v in os.environ.items() if k in _BEDROCK_KEYS and v}


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
            model="eu.anthropic.claude-haiku-4-5-20251001-v1:0",
            allowed_tools=["Read", "Glob", "Bash"],
            permission_mode="bypassPermissions",
            setting_sources=["local"],
            env=bedrock_env(),
        ),
    ):
        print_verbose(message)
        if hasattr(message, "result"):
            print("\n" + message.result)


if __name__ == "__main__":
    asyncio.run(main())
