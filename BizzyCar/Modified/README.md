# BizzyCar Applied AI Starter

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


#  Quick Reference - Real API

## One-Minute Setup


```bash
      
export OPENAI_AVAILABLE=TRUE
export USE_REAL_API=TRUE
export LLM_API_KEY=
export LLM_BASE_URL=
exprot LLM_MODEL= "gpt-4"

# Run with real API
python -m src.main --input data/messages.json --output results.json
```


## Test Integration

```bash
# Run full test suite
python test_API_integration.py

```

## Python Code Examples

### Basic Usage
```python
import asyncio
import os
from src.processing import process_notes
notes = ["2018 Camry in for oil change and tire service"]
results = asyncio.run(process_notes(notes))

print(results[0]['vehicle_make'])  # Toyota
print(results[0]['service_intent'])  # ['oil_change', 'tire_pressure']
print(results[0]['raw_extraction_confidence'])  # 0.9
```

### API Integration
```python
from openai import OpenAI

client = OpenAI(
    api_key="",
    base_url=""
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Extract service info from..."}],
    max_tokens=500
)

print(response.choices[0].message.content)
```

## File Locations

| File | Purpose | Location |
|------|---------|----------|
| Model Client | Handles mock & real API | `src/model_client.py` |
| Processing | Main extraction pipeline | `src/processing.py` |

## Common Issues

| Issue | Solution |
|-------|----------|
| "OpenAI package required" | `pip install openai` |
| API returns 402 | Need to top up AI credits |
| USE_REAL_API not working | Check environment variable: `echo USE_REAL_API` |
| Slow responses | Normal (~400ms). Use mock for testing |


