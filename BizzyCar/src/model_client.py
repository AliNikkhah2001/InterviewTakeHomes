import os, random, re, json, asyncio
from typing import Dict, Any
from .schemas import Extraction

class MockLLMClient:
    """
    Simulates an LLM with occasional hallucinations and malformed JSON.
    Controls via environment variables:
      MOCK_BAD_JSON_RATE (default 0.2)
      MOCK_HALLUCINATION_RATE (default 0.25)
    """
    def __init__(self):
        self.bad_json_rate = float(os.getenv("MOCK_BAD_JSON_RATE", "0.2"))
        self.hallu_rate = float(os.getenv("MOCK_HALLUCINATION_RATE", "0.25"))
        random.seed(42)

    async def extract(self, text: str) -> str:
        intents = []
        t = text.lower()
        if "oil" in t: intents.append("oil_change")
        if "tire" in t: intents.extend(["tire_pressure" if "pressure" in t else "tire_rotation"])
        if "battery" in t: intents.append("battery")
        if "brak" in t: intents.append("brake_service")
        if "ac" in t or "a/c" in t: intents.append("ac_service")
        if "check-engine" in t or "check engine" in t: intents.append("engine_diagnostic")
        if not intents:
            intents.append("unknown")

        make = None
        model = None
        year = None
        m = re.search(r"(20\d{2}|19\d{2})", text)
        if m:
            year = int(m.group(1))
        if "camry" in t: make, model = "Toyota", "Camry"
        if "accord" in t: make, model = "Honda", "Accord"
        if "rogue" in t: make, model = "Nissan", "Rogue"
        if "f-150" in t or "f150" in t: make, model = "Ford", "F-150"

        if random.random() < self.hallu_rate:
            intents.append("inspection")
            if year: year += random.choice([1, -1])

        data = {
            "vin_detected": bool(re.search(r"\b[0-9A-Z]{11,17}\b", text)),
            "vehicle_make": make,
            "vehicle_model": model,
            "year": year,
            "service_intent": list(dict.fromkeys(intents)),
            "urgency": "medium",
            "raw_extraction_confidence": round(random.uniform(0.55, 0.9), 2),
            "notes": None
        }
        payload = json.dumps(data)
        if random.random() < self.bad_json_rate:
            payload = payload[:-1]  # drop closing brace
        await asyncio.sleep(0)
        return payload

async def get_client():
    return MockLLMClient()
