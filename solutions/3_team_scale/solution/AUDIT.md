# FleetOS API — Pre-release Audit

| Category | Light | Summary |
| --- | --- | --- |
| Data correctness | 🟡 | BMW-X5-114 is API-`active` but has an unresolved high-severity brake incident. |
| Contract | 🟢 | All endpoints return documented status codes and shapes; 404 on unknown ID. |
| Security | 🟡 | CORS `allow_origins=["*"]` and no auth on any route — fine for the lab, not for prod. |

## db-auditor

- **BMW-X5-114** — API says `active`; DB `incidents` has unresolved `severity=high` "brake warning light intermittent" — should surface as `maintenance`.
- **BMW-iX1-204** — API priority 78; DB shows no fuel-log anomaly, depot München has 2 bays free — agrees.
- 4 other sampled vehicles: API and DB consistent.

## contract-tester

| Endpoint | Expected | Actual | ✓/✗ | Note |
| --- | --- | --- | --- | --- |
| `GET /vehicles` | 200, list | 200, 18 items | ✓ | sorted by priority desc |
| `GET /vehicles/BMW-X5-114/maintenance` | 200, forecast | 200 | ✓ | all required fields present |
| `GET /vehicles/UNKNOWN/maintenance` | 404 | 404 | ✓ | clean error body |
| `GET /vehicles/BMW-X5-114/history` | 200, list | 200, 3 records | ✓ | most-recent first |

## security-reviewer

- `main.py:9` — **medium** — `allow_origins=["*"]` permits any browser origin.
- `main.py` — **medium** — no authentication or rate limiting on any route.
- No hardcoded secrets found.
- No SQL/string concatenation found (CSV-backed, no DB layer).
- No `subprocess`/shell calls found.

## Release decision

**GO** — no 🔴 findings. Track the two 🟡 items (BMW-X5-114 status mismatch,
open CORS/auth) as follow-ups before production rollout.
