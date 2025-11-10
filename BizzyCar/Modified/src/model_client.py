import os, random, re, json, asyncio
from typing import Dict, Any, Optional
from .schemas import Extraction

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class RealAPIClient:
    """
    Real LLM client using any OpenAI-compatible API provider.
    Supports: OpenRouter, Together AI, Ollama, or any OpenAI-compatible endpoint.
    """
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4"):
        from openai import OpenAI
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    async def extract(self, text: str) -> str:
        """Extract service insights using real GPT-4 API."""
        prompt = f"""Extract service information from this dealership note. Return JSON only.

Text: {text}

Return valid JSON with these fields:
{{
  "vin_detected": boolean,
  "vehicle_make": string or null,
  "vehicle_model": string or null,
  "year": integer (1980-2100) or null,
  "service_intent": array of strings from ["engine_diagnostic", "oil_change", "tire_rotation", "tire_pressure", "battery", "brake_service", "ac_service", "inspection", "unknown"],
  "urgency": "low"|"medium"|"high",
  "raw_extraction_confidence": float 0.0-1.0,
  "notes": string or null
}}

Rules:
- If you detect VIN (11-17 alphanumeric), set vin_detected to true
- Extract year from text (4-digit number)
- Identify service needs from keywords
- Set confidence based on how clear the text is
- Only include actual services mentioned, use "unknown" if none found"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )

            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f" AI API error: {str(e)}")

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
    """Get either real API client or mock client based on env vars.
    
    Supports any OpenAI-compatible provider:
    - OpenRouter (https://openrouter.ai/api/v1)
    - Together AI (https://api.together.ai/v1)
    - Ollama (http://localhost:11434/v1)
    - Any custom OpenAI-compatible endpoint
    """
    use_real_api = os.getenv("USE_REAL_API", "false").lower() == "true"
    if use_real_api:
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL")
        model = os.getenv("LLM_MODEL", "gpt-4")
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable not set")
        if not base_url:
            raise ValueError("LLM_BASE_URL environment variable not set")

        return RealAPIClient(api_key, base_url, model)
    else:
        return MockLLMClient()
