# BizzyCar Applied AI Starter

This repo contains a minimal starter kit for the **Applied AI Engineer** take‑home. See `challenge.md` for the full brief.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run tests
pytest -q

# Run the CLI (reads data/messages.json)
python -m src.main --input data/messages.json --output sample_output.json

# Or run the API
uvicorn src.main:app --reload --port 8000
# Then:
curl -s http://127.0.0.1:8000/healthz
curl -s -X POST http://127.0.0.1:8000/analyze -H "content-type: application/json" -d @data/messages.json | jq .
```

## Files
- `src/schemas.py` — Pydantic models for strict validation.
- `src/model_client.py` — Mock LLM client (can optionally call a real API if env vars provided).
- `src/processing.py` — Orchestration: prompts, retries, fallback policy, PII redaction, calibration.
- `src/validators.py` — Output validation & guardrails.
- `src/main.py` — CLI and FastAPI wiring.
- `tests/` — Small tests covering happy path and hallucination handling.
- `data/messages.json` — Sample inputs.
