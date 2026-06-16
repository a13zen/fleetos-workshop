# Challenge 3 - Solution

Reference implementation for every step. To run end-to-end:

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY
./reset.sh

# terminal 1
uvicorn fleetos_api.main:app --port 8001

# terminal 2
python step1_minimal.py --verbose
python step3_two_sources.py --verbose
python step4_analyst.py --verbose      # → MONDAY_BRIEFING.md, briefing.json
python step5_orchestrator.py --verbose # → OPS_PLAN.md, emails/
```

`step2_fleetos_mcp.py` is not run directly - steps 3–5 spawn it as a
stdio subprocess.
