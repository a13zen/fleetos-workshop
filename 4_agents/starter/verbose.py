"""
Shared --verbose printer for all agent scripts in this challenge.

Import `print_verbose` and call it on every message yielded by `query()`.
Pass --verbose on the command line to see the agent's full loop: narration,
tool calls with their key argument, truncated tool results, and a
turns/duration/cost footer. Pass --no-color to disable ANSI colors
(auto-disabled when stdout isn't a TTY).

Importing this module also loads `.env` from this directory, so every
script gets ANTHROPIC_API_KEY without an explicit `export`.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

_VERBOSE = "--verbose" in sys.argv
_COLOR = sys.stdout.isatty() and "--no-color" not in sys.argv

CYAN, DIM, RED, ITALIC, RESET = "36", "2", "31", "3", "0"


def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _COLOR else s


def _truncate(s: str, width: int = 100) -> str:
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= width else s[: width - 1] + "…"


def _truncate_block(s: str, lines: int = 3, width: int = 200) -> str:
    parts = s.splitlines() or [""]
    out = parts[:lines]
    if len(parts) > lines or len(s) > width:
        out.append(f"… ({len(parts)} lines)")
    return "\n".join("    " + ln for ln in out)


def _summarize_input(name: str, inp: dict) -> str:
    if name == "Bash":
        return _truncate(inp.get("command", ""))
    if name in ("Read", "Edit", "NotebookEdit"):
        return inp.get("file_path", "")
    if name == "Write":
        content = inp.get("content", "")
        n = content.count("\n") + 1 if content else 0
        return f"{inp.get('file_path', '')} ({n} lines)"
    if name in ("Glob", "Grep"):
        return inp.get("pattern", "")
    if name in ("Task", "Agent"):
        return inp.get("description") or inp.get("prompt", "")[:80]
    return _truncate(", ".join(f"{k}={v!r}" for k, v in inp.items()))


def _result_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("content") or str(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def print_verbose(message) -> None:
    if not _VERBOSE:
        return

    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                for line in block.text.splitlines():
                    print(f"  {line}")
            elif isinstance(block, ToolUseBlock):
                arg = _summarize_input(block.name, block.input)
                print(_c(CYAN, f"  → {block.name:<6} {arg}"))
            elif isinstance(block, ThinkingBlock):
                first = (block.thinking or "").strip().splitlines()[:1]
                if first:
                    print(_c(DIM, _c(ITALIC, f"  · thinking: {_truncate(first[0], 80)}")))

    elif isinstance(message, UserMessage):
        if not isinstance(message.content, list):
            return
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                text = _result_text(block.content)
                if block.is_error:
                    print(_c(RED, f"  ✗ {_truncate(text, 100)}"))
                else:
                    print(_c(DIM, "  ←"))
                    print(_c(DIM, _truncate_block(text)))

    elif isinstance(message, ResultMessage):
        secs = message.duration_ms / 1000
        cost = f"${message.total_cost_usd:.4f}" if message.total_cost_usd else "$-"
        print(_c(DIM, f"\n  ── {message.num_turns} turns · {secs:.1f}s · {cost} ──"))
