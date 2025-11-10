# BizzyCar — Applied AI Engineer Take‑Home Challenge (2–3 hours)

## Context
BizzyCar helps dealerships retain service customers through personalized communication and intelligent automation.
This exercise focuses on **designing and implementing a small backend system that orchestrates an AI model**. You are **not** expected to train models; instead, demonstrate solid software engineering around AI integration: data ingestion, prompt design, schema validation, retries/fallbacks, and handling hallucinations/errors.

You can complete this with **local-only code** and the provided **mock LLM client**. If you prefer to call a real model API, that’s optional. Keep the scope tight and runnable in minutes.

## Scenario
Dealerships send batches of **free‑form service notes and customer messages**. We want to automatically extract structured insights.

Example input text:
> "2018 Camry in for check-engine light and oil change. Customer also mentioned tire pressure low."

Target output (JSON):
```json
{
  "vin_detected": false,
  "vehicle_make": "Toyota",
  "vehicle_model": "Camry",
  "year": 2018,
  "service_intent": ["engine_diagnostic", "oil_change", "tire_pressure"],
  "urgency": "medium",
  "raw_extraction_confidence": 0.83,
  "notes": "optional"
}
```

## Your Task
Build a small **Python service** (CLI or API) that:
1. **Ingests** an array of messages (from `data/messages.json`, a file path, or POST `/analyze`).  
2. **Prompts/calls an AI model** (use our mock by default; real API optional).  
3. **Validates and parses** the model response against a strict schema (Pydantic provided).  
4. **Handles hallucinations & errors** with **retry rules** (e.g., add stricter instructions, reduce temperature, or fall back to a rule‑based extractor).  
5. **Logs** inputs/outputs/errors to structured logs (JSON lines). Redact obvious PII (emails, phones).

### Minimum Requirements
- Implement `process_notes(notes: list[str]) -> list[dict]` that returns **validated** items.
- Include at least one **retry strategy** and one **fallback** path.
- Provide **sample input** and **your produced output** files.
- Add a small **unit test** that exercises a happy path and a hallucination case.

### Optional (nice-to-have)
- FastAPI app exposing `POST /analyze` and `GET /healthz`.
- A tiny **confidence calibration** step (e.g., heuristics to down‑weight low‑evidence outputs).
- Dockerfile.

## What to Submit
- Your code (you can modify anything in `src/`).
- Short **README** (1–2 pages): architecture sketch (ASCII ok), error‑handling, trade‑offs, what you’d do next.
- Artifacts: `sample_output.json`, and if you run the API, a `curl` example.

## Rubric
| Area | What “good” looks like |
|------|-------------------------|
| System Design | Clear separation of concerns: input -> model client -> validation -> post‑processing |
| API Integration | Robust to malformed outputs, timeouts, and rate limits; retries/fallbacks are justified |
| Reliability | Deterministic tests; logs with context; basic PII redaction |
| Code Quality | Readable, typed, small functions, minimal dependencies |
| Communication | README explains constraints, trade‑offs, and next steps |
| Bonus | Pydantic schema, structured logging, basic calibration or rule‑based guardrails |

## Constraints
- Keep runtime < 5 minutes on a laptop; no paid services required.
- Python 3.10+ recommended.
- If you use a real provider, **do not commit keys**; use environment variables.

Good luck — we’re excited to see your approach!
