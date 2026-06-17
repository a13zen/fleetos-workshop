"""
Stage 1 — Minimal agent loop using the Anthropic SDK directly.

Uses the anthropic Python library (not claude-agent-sdk) to run a simple
agentic loop that reads fleet CSV data and summarises fleet status.

Run:
    python step1_agent.py

Requires:
    ANTHROPIC_API_KEY env var (or set in .env)
"""

import os
import sys
import csv
from pathlib import Path
import anthropic

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
FLEET_DATA_DIR = HERE.parent / "fleetos_api" / "data"

MODEL = "claude-haiku-4-5"

# Tool definition: read a CSV file and return its contents as a string
TOOLS = [
    {
        "name": "read_csv_file",
        "description": (
            "Read a CSV file from disk and return its contents as a formatted string. "
            "Use this to access fleet vehicle data or service history."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Absolute or relative path to the CSV file to read. "
                        "Available files: "
                        f"{FLEET_DATA_DIR}/vehicles.csv (vehicle list), "
                        f"{FLEET_DATA_DIR}/service_history.csv (service records)"
                    ),
                }
            },
            "required": ["path"],
        },
    }
]


def read_csv_file(path: str) -> str:
    """Read a CSV file and return its contents as a formatted string."""
    try:
        resolved = Path(path)
        if not resolved.is_absolute():
            # Try relative to fleet data dir first, then cwd
            candidate = FLEET_DATA_DIR / path
            if candidate.exists():
                resolved = candidate
            else:
                resolved = HERE / path

        if not resolved.exists():
            # Last resort: check if just the filename matches something in FLEET_DATA_DIR
            filename = Path(path).name
            candidate = FLEET_DATA_DIR / filename
            if candidate.exists():
                resolved = candidate
            else:
                return f"Error: file not found: {path}"

        rows = []
        with open(resolved, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))

        if not rows:
            return "Empty CSV file."

        headers = list(rows[0].keys())
        lines = [", ".join(headers)]
        for row in rows:
            lines.append(", ".join(str(row.get(h, "")) for h in headers))
        return "\n".join(lines)

    except Exception as e:
        return f"Error reading {path}: {e}"


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Dispatch a tool call and return the result as a string."""
    if tool_name == "read_csv_file":
        return read_csv_file(tool_input["path"])
    return f"Unknown tool: {tool_name}"


def run_agent(prompt: str, verbose: bool = False) -> str:
    """
    Run a simple agentic loop using the Anthropic SDK.
    Continues until the model stops calling tools.
    Returns the final text response.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    messages = [{"role": "user", "content": prompt}]
    MAX_TURNS = 20
    turn = 0

    while True:
        turn += 1
        if turn > MAX_TURNS:
            print(f"Warning: agent exceeded {MAX_TURNS} turns, stopping")
            break
        if verbose:
            print(f"\n[Turn {turn}] Sending to model...")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        if verbose:
            print(f"[Turn {turn}] Stop reason: {response.stop_reason}")

        # Append assistant response to the conversation
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "max_tokens":
            print(f"Warning: response truncated at turn {turn}")
            break

        # If no more tool calls, we're done
        if response.stop_reason == "end_turn":
            # Extract text from the final response
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if verbose:
                    print(f"[Turn {turn}] -> Tool: {block.name}({block.input})")

                result = process_tool_call(block.name, block.input)

                if verbose:
                    preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"[Turn {turn}] <- Result preview: {preview}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if not tool_results:
            # No tools called but stop_reason wasn't end_turn — stop anyway
            break

        # Append tool results as a user turn
        messages.append({"role": "user", "content": tool_results})

    # Fallback: extract text from last assistant response
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("Fleet Status Agent — Stage 1")
    print("=" * 50)

    prompt = (
        f"You have access to fleet CSV files. "
        f"The vehicles file is at {FLEET_DATA_DIR}/vehicles.csv and "
        f"the service history is at {FLEET_DATA_DIR}/service_history.csv. "
        "Please read the vehicles CSV and summarise the fleet status: "
        "how many vehicles are there, what makes/models are represented, "
        "which vehicles have no assigned driver, and what is the mileage range? "
        "Then read the service history and note the most recent service date for each vehicle. "
        "Provide a concise fleet status summary suitable for a manager."
    )

    result = run_agent(prompt, verbose=verbose)
    print("\n" + result)


if __name__ == "__main__":
    main()
