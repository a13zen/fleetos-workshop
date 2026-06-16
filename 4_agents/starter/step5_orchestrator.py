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

# (intentionally empty — Claude Code fills this in during Step 5)
