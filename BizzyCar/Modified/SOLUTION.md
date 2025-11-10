# BizzyCar Applied AI Engineer — Solution & Documentation

## Overview

This solution implements a robust backend system for extracting structured service insights from free-form dealership notes and customer messages. The pipeline orchestrates an AI model (mock or real API) with comprehensive error handling, validation, and fallback strategies.

**All minimum requirements met:**
-  Processes sample input via mock AI client (extensible to real APIs)
-  Retry strategy for low confidence and hallucinations (3 attempts with exponential backoff)
-  Fallback path using rule-based keyword extraction
-  Sample input (`data/messages.json`) and output (`sample_output.json`)
-  Comprehensive unit tests covering happy path and edge cases

**Optional features implemented:**
-  FastAPI app with `/healthz` and `/analyze` endpoints
-  Confidence calibration with heuristics
-  Structured JSONL logging with full event tracking
-  PII redaction (emails, phone numbers)
-  Hallucination detection (spurious 'inspection' intents)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Input (CLI or API)                       │
│         (batch of service notes from dealerships)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   Preprocessing                              │
│  • Truncate to 2000 chars (token limit safety)              │
│  • PII Redaction (emails, phone numbers)                    │
│  • Log event: extraction_start                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              Robust Extraction with Retries                  │
│                (3 attempts, exponential backoff)             │
│                                                               │
│  Attempt 1-3:                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 1. Call Model (mock or real API)                       │  │
│  │ 2. Parse JSON response                                 │  │
│  │ 3. Detect Hallucinations                               │  │
│  │    • Check for spurious 'inspection' intent            │  │
│  │ 4. Validate Confidence                                 │  │
│  │    • Reject if < 0.6 and no strong signal              │  │
│  │ 5. Calibrate Confidence                                │  │
│  │    • Down-weight: unknown intents, missing vehicle     │  │
│  │    • Boost: strong signals + good confidence           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Exceptions Caught:                                          │
│  • ModelBadJSON: malformed JSON → retry                      │
│  • ModelLowConfidence: low confidence → retry                │
│  • HallucationDetected: spurious intents → retry             │
└──────────────────────┬──────────────────────────────────────┘
                       │ (success)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              Fallback (if retries exhausted)                 │
│                  Rule-Based Extractor                        │
│                                                               │
│  • Keyword matching for service intents                      │
│  • Basic vehicle model/year extraction                       │
│  • Confidence: 0.45 (conservative)                           │
│  • Mark source: fallback_rule_based                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              Pydantic Validation & Coercion                  │
│                                                               │
│  • Strict schema enforcement (types, ranges)                 │
│  • ServiceIntent enum validation                             │
│  • Confidence must be [0.0, 1.0]                             │
│  • Year must be in [1980, 2100]                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              Structured Logging (JSONL)                      │
│                                                               │
│  Events logged:                                              │
│  • extraction_start: input length                            │
│  • extraction_success: method, confidence                    │
│  • extraction_retry_failed: error type, message              │
│  • extraction_error: unexpected errors                       │
│  • validation_warning: warnings from validator               │
│  • extraction_complete: final result metadata                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Output (JSON)                             │
│  • Validated Extraction object                              │
│  • _extraction_method: "model" or "fallback"                │
│  • Ready for downstream processing                          │
└──────────────────────────────────────────────────────────────┘
```

---

## Error Handling & Retry Strategy

### Retry Mechanism (Tenacity)
- **Max attempts:** 3
- **Backoff:** Exponential (multiplier=0.2, min=0.2s, max=1.5s)
- **Triggers:**
  - `ModelBadJSON`: JSON parsing fails → malformed output from model
  - `ModelLowConfidence`: confidence < 0.6 and no strong textual signal
  - `HallucationDetected`: spurious 'inspection' in service intents

### Fallback Strategy
If all retries fail, use rule-based extraction:
- Scans input text for keywords (oil, tire, battery, brake, ac, check engine)
- Extracts vehicle model/year via regex
- Conservative confidence: 0.45
- Marked with `notes="fallback_rule_based"` for observability


---

## Hallucination Detection & Calibration

### Hallucination Detection
The mock client intentionally injects spurious 'inspection' intents. Detection:
```python
if "inspection" in service_intents and "inspection" not in original_text:
    raise HallucationDetected(...)
```
This catches obvious hallucinations without false positives.

### Confidence Calibration
Adjusts reported confidence based on evidence:

| Scenario | Adjustment | Rationale |
|----------|-----------|-----------|
| Only "unknown" intent | Down to ≤0.45 | Low signal |
| Missing vehicle make | Down by 0.15 | Weak extraction |
| Strong signals (oil, brake, etc.) + conf>0.6 | Boost by 0.05 | High signal |

**Result:** More realistic confidence scores for downstream decision-making.

---

## Implementation Details

### Key Files

| File | Purpose |
|------|---------|
| `src/processing.py` | Core pipeline: retries, fallback, calibration, logging |
| `src/model_client.py` | Mock LLM with tunable hallucination/bad-JSON rates |
| `src/schemas.py` | Pydantic models for strict validation |
| `src/validators.py` | Output validation & guardrails |
| `src/main.py` | CLI and FastAPI entry points |
| `tests/test_pipeline.py` | Comprehensive test suite (7 tests) |

### Structured Logging (JSONL)
All events written to `pipeline.jsonl` with:
- **Timestamp:** ISO format, UTC
- **Event type:** extraction_start, extraction_success, extraction_retry_failed, etc.
- **Context:** input index, method, confidence, error details
- **PII redacted:** Original input not logged

Example log entry:
```json
{
  "timestamp": "2025-11-10T18:45:30.123456",
  "event_type": "extraction_complete",
  "input_idx": 0,
  "method": "model",
  "intents": ["oil_change", "tire_pressure"],
  "confidence": 0.56
}
```

### PII Redaction
Applied to all logged/processed text:
- Email: `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` → `<redacted_email>`
- Phone: `\+?\d[\d\-\s]{7,}\d` → `<redacted_phone>`

---

## Test Coverage

All tests pass (7/7):

1. **test_process_notes_happy_path**: Clear input → correct extraction
2. **test_process_notes_hallucination_or_badjson**: Malformed data → graceful fallback
3. **test_pii_redaction**: Emails & phones properly redacted
4. **test_hallucination_detection**: Spurious 'inspection' caught
5. **test_confidence_calibration**: Confidence adjusted based on signals
6. **test_batch_processing**: Multiple notes processed correctly
7. **test_logging_output**: JSONL logs written and valid



---

## Sample Output

Input: `data/messages.json` (5 service notes)

Output: `sample_output.json` (5 extracted records)

**Key observations:**
- Note 1 (Camry, oil + check-engine): Multi-intent extraction, correct vehicle
- Note 2 (Accord, braking + VIN): VIN detected, correct service intent
- Note 3 (Rogue, tire + AC): Multiple services, correct year
- Note 4 (generic question): Fallback used → "unknown" intent, low confidence (0.45)
- Note 5 (F-150, battery): Correct extraction from less explicit text

---

## Usage

### CLI
```bash
python -m src.main --input data/messages.json --output results.json
```

### API
```bash
# Start server
uvicorn src.main:app --reload --port 8000

# Health check
curl -s http://127.0.0.1:8000/healthz

# Analyze notes
curl -X POST http://127.0.0.1:8000/analyze \
  -H "content-type: application/json" \
  -d '{
    "messages": [
      "2018 Camry in for oil change",
      "Brake grinding noise on 2015 Accord"
    ]
  }' | jq .
```

---

## Next Steps & Future Improvements

### Short-term (high priority)
1. **Real API integration:** Add OpenAI/Claude clients via env vars
2. **Confidence thresholds:** Configurable cutoffs for retry logic
3. **More hallucination patterns:** Detect inconsistent vehicle info, impossible years
4. **Async batch processing:** Parallel requests to API (with rate limiting)

### Medium-term
1. **Fine-tuning:** Train model on dealership-specific service notes
2. **Per-intent confidence:** Separate confidence for each service_intent
3. **Structured output metadata:** Add extraction_method, retry_count, fallback_reason
4. **Monitoring dashboard:** Visualize extraction success rate, confidence distribution

### Long-term
1. **Active learning:** Label ambiguous cases for retraining
2. **Multi-model ensemble:** Vote between model and rule-based extractor
3. **Customer feedback loop:** Track which extractions led to good/poor outcomes
4. **Dealership-specific models:** Customize extraction for each dealership's domain


## How to Evaluate

1. **Run tests:** `pytest tests/test_pipeline.py -v` → All 7 pass
2. **Check sample output:** `sample_output.json` → Matches expected schema
3. **Review logs:** `pipeline.jsonl` → Events with timestamps and context
4. **Try the API:** Start server and curl `/analyze` endpoint
5. **Inspect code:** Clear separation of concerns, typed functions, docstrings

