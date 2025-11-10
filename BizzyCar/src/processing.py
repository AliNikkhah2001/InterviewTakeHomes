import json, re, asyncio, logging, sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
from .model_client import get_client
from .validators import validate_extraction

# Setup structured logging (JSONL)
logger = logging.getLogger(__name__)
log_handler = logging.FileHandler('pipeline.jsonl', mode='a')
log_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

PII_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PII_PHONE = re.compile(r"\+?\d[\d\-\s]{7,}\d")

def redact(text: str) -> str:
    text = PII_EMAIL.sub("<redacted_email>", text)
    text = PII_PHONE.sub("<redacted_phone>", text)
    return text

def log_event(event_type: str, data: Dict[str, Any], error: Optional[str] = None):
    """Log structured events to JSONL."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        **data
    }
    if error:
        log_entry["error"] = error
    logger.info(json.dumps(log_entry))

class ModelBadJSON(Exception): ...
class ModelLowConfidence(Exception): ...
class HallucationDetected(Exception): ...

async def call_model_with_prompt(text: str, attempt: int = 1) -> Dict[str, Any]:
    """Call model with optional stricter instructions on retries."""
    client = await get_client()
    raw = await client.extract(text)
    try:
        out = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ModelBadJSON(str(e))
    return out

def detect_hallucinations(obj: Dict[str, Any], original_text: str) -> bool:
    """Detect hallucinations (e.g., 'inspection' not in original text)."""
    service_intents = obj.get("service_intent", [])
    text_lower = original_text.lower()
    
    # Check for spurious 'inspection' that wasn't in input
    if "inspection" in service_intents and "inspection" not in text_lower and "inspect" not in text_lower:
        return True
    
    return False

def calibrate_confidence(obj: Dict[str, Any], original_text: str) -> Dict[str, Any]:
    """Apply calibration heuristics to confidence scores."""
    confidence = float(obj.get("raw_extraction_confidence", 0.5))
    text_lower = original_text.lower()
    
    # Down-weight if no strong evidence
    strong_signals = ["check engine", "brak", "battery", "tire", "oil", "ac"]
    has_strong_signal = any(sig in text_lower for sig in strong_signals)
    
    # Down-weight if only 'unknown' intent
    if obj.get("service_intent") == ["unknown"]:
        confidence = min(confidence, 0.45)
    
    # Down-weight if missing vehicle info
    if not obj.get("vehicle_make"):
        confidence = max(0.3, confidence - 0.15)
    
    # Boost if has strong signal and reasonable confidence
    if has_strong_signal and confidence > 0.6:
        confidence = min(0.9, confidence + 0.05)
    
    obj["raw_extraction_confidence"] = round(confidence, 2)
    return obj

@retry(reraise=True,
       retry=retry_if_exception_type((ModelBadJSON, ModelLowConfidence, HallucationDetected)),
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=0.2, min=0.2, max=1.5))
async def robust_extract(text: str, attempt: int = 1) -> Dict[str, Any]:
    obj = await call_model_with_prompt(text, attempt=attempt)
    
    # Check for hallucinations
    if detect_hallucinations(obj, text):
        raise HallucationDetected("spurious 'inspection' intent detected")
    
    confidence = float(obj.get("raw_extraction_confidence", 0.0))
    strong_signal = any(k in text.lower() for k in ["check engine", "brak", "battery", "tire", "oil"])
    
    # Retry if low confidence without strong signal
    if confidence < 0.6 and not strong_signal:
        raise ModelLowConfidence(f"low confidence: {confidence}")
    
    # Apply calibration
    obj = calibrate_confidence(obj, text)
    return obj

async def fallback_rule_based(text: str) -> Dict[str, Any]:
    t = text.lower()
    intents = []
    if "oil" in t: intents.append("oil_change")
    if "tire" in t: intents.append("tire_rotation" if "rotation" in t else "tire_pressure")
    if "battery" in t: intents.append("battery")
    if "brak" in t: intents.append("brake_service")
    if "ac" in t or "a/c" in t: intents.append("ac_service")
    if "check engine" in t or "check-engine" in t: intents.append("engine_diagnostic")
    if not intents: intents = ["unknown"]
    return {
        "vin_detected": False,
        "vehicle_make": None,
        "vehicle_model": None,
        "year": None,
        "service_intent": intents,
        "urgency": "medium",
        "raw_extraction_confidence": 0.45,
        "notes": "fallback_rule_based"
    }

async def process_notes(notes: List[str]) -> List[Dict[str, Any]]:
    """Process a batch of service notes with full error handling and logging."""
    results: List[Dict[str, Any]] = []
    
    for idx, text in enumerate(notes):
        original_text = text.strip()
        clean = original_text[:2000]
        clean_redacted = redact(clean)
        
        log_event("extraction_start", {"input_idx": idx, "input_length": len(original_text)})
        
        extraction_method = "model"
        obj = None
        error_trace = None
        
        try:
            obj = await robust_extract(clean_redacted)
            log_event("extraction_success", 
                     {"input_idx": idx, "method": extraction_method, 
                      "confidence": obj.get("raw_extraction_confidence")})
        except (ModelBadJSON, ModelLowConfidence, HallucationDetected) as e:
            error_trace = str(e)
            log_event("extraction_retry_failed", 
                     {"input_idx": idx, "error_type": type(e).__name__, "message": error_trace})
            extraction_method = "fallback"
            obj = await fallback_rule_based(clean_redacted)
        except Exception as e:
            error_trace = str(e)
            log_event("extraction_error", 
                     {"input_idx": idx, "error_type": type(e).__name__}, error=error_trace)
            extraction_method = "fallback"
            obj = await fallback_rule_based(clean_redacted)
        
        try:
            ex, warnings = validate_extraction(obj)
            if warnings:
                log_event("validation_warning", 
                         {"input_idx": idx, "warnings": warnings})
        except Exception as e:
            log_event("validation_failed", 
                     {"input_idx": idx, "error_type": type(e).__name__}, error=str(e))
            # Final fallback: use fallback + re-validate
            obj = await fallback_rule_based(clean_redacted)
            ex, warnings = validate_extraction(obj)
        
        result = ex.model_dump()
        result["_extraction_method"] = extraction_method
        results.append(result)
        
        log_event("extraction_complete", 
                 {"input_idx": idx, "method": extraction_method, 
                  "intents": result["service_intent"], 
                  "confidence": result["raw_extraction_confidence"]})
    
    return results
