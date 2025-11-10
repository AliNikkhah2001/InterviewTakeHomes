# BizzyCar AI Service — Quick Start

## 30-Second Setup

```bash
cd /Users/alinikkhah/Desktop/bizzycar_applied_ai_takehome\ \(4\)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run Tests

```bash
pytest tests/test_pipeline.py -v
# Output: 7 passed ✅
```

## CLI Usage

```bash
# Process sample data
python -m src.main --input data/messages.json --output results.json

# Check results
cat results.json | jq '.items[0]'
```

## API Usage

```bash
# Terminal 1: Start server
uvicorn src.main:app --reload --port 8000

# Terminal 2: Health check
curl -s http://127.0.0.1:8000/healthz
# {"status":"ok"}

# Terminal 2: Analyze notes
curl -X POST http://127.0.0.1:8000/analyze \
  -H "content-type: application/json" \
  -d '{
    "messages": [
      "2018 Camry in for oil change and tire pressure check",
      "Brake grinding on 2015 Accord, customer concerned about safety"
    ]
  }' | jq '.items[] | {vehicle: "\(.vehicle_make) \(.vehicle_model)", intents: .service_intent, confidence: .raw_extraction_confidence}'

# Output:
# {
#   "vehicle": "Toyota Camry",
#   "intents": ["oil_change", "tire_pressure"],
#   "confidence": 0.56
# }
# {
#   "vehicle": "Honda Accord",
#   "intents": ["brake_service"],
#   "confidence": 0.56
# }
```

## File Structure

```
src/
├── main.py                    # CLI and FastAPI entry
├── processing.py              # Core pipeline (retries, fallback, logging)
├── model_client.py            # Mock LLM (tunable hallucinations)
├── schemas.py                 # Pydantic models
└── validators.py              # Output validation

tests/
└── test_pipeline.py           # 7 comprehensive tests

data/
└── messages.json              # Sample input (5 notes)

sample_output.json             # Expected output
pipeline.jsonl                 # Structured logs (auto-generated)
```

## Key Features

| Feature | Details |
|---------|---------|
| **Retries** | 3 attempts with exponential backoff on bad JSON/low confidence/hallucinations |
| **Fallback** | Rule-based keyword extraction when model fails |
| **Hallucination Detection** | Catches spurious 'inspection' intents not in input |
| **Confidence Calibration** | Heuristics to adjust confidence based on evidence |
| **PII Redaction** | Emails and phone numbers redacted in logs |
| **Logging** | JSONL format with timestamps, event types, and context |

## Customize Behavior

```bash
# Increase hallucination rate (for testing)
export MOCK_HALLUCINATION_RATE=0.5
export MOCK_BAD_JSON_RATE=0.3
python -m src.main --input data/messages.json --output results.json
```

## Logs

```bash
# View all events
cat pipeline.jsonl | jq .

# Filter by event type
cat pipeline.jsonl | jq 'select(.event_type == "extraction_complete")'

# Find errors
cat pipeline.jsonl | jq 'select(.error_type != null)'
```

## Output Schema

Each extracted item includes:

```json
{
  "vin_detected": boolean,
  "vehicle_make": string | null,
  "vehicle_model": string | null,
  "year": integer | null,                    # 1980-2100
  "service_intent": ["engine_diagnostic", "oil_change", ...],
  "urgency": "low" | "medium" | "high",
  "raw_extraction_confidence": 0.0-1.0,
  "notes": string | null,
  "_extraction_method": "model" | "fallback"  # Internal tracking
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tests fail | Check `python --version` (3.10+ required) |
| API won't start | Port 8000 in use? Try `--port 8001` |
| Low confidence | Check logs: `cat pipeline.jsonl` for details |
| Logs not appearing | Logs written to `pipeline.jsonl` in working directory |

## Next Steps

- Read `SOLUTION.md` for full architecture and design decisions
- Check `sample_output.json` for expected output format
- Review `tests/test_pipeline.py` for testing patterns
- Modify `src/` to add real LLM API integration

---

**Questions?** Check `SOLUTION.md` (comprehensive documentation) or inspect source code (well-commented).
