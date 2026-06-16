---
name: fleet-audit
description: Pre-release audit of a FleetOS service - data correctness, contract, security. Invoke as /fleet-audit [dir].
---

Run a pre-release audit of `$ARGUMENTS` (default `../fleetos_api`).

Launch the `db-auditor`, `contract-tester` and `security-reviewer`
subagents **in parallel** against the target directory. Combine their
findings into `AUDIT.md` with:

1. A traffic-light summary table at the top - one row per category
   (Data correctness · Contract · Security), each with a 🟢/🟡/🔴 light
   and a one-line summary.
2. One `##` section per subagent containing its raw findings verbatim.
3. A final `## Release decision` line: **GO** or **NO-GO**, with one
   sentence of justification.

If any 🔴 finding exists, the decision must be NO-GO.
