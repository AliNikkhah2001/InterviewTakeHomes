from typing import Any, Dict, List, Tuple
from pydantic import ValidationError
from .schemas import Extraction

def validate_extraction(obj: Dict[str, Any]) -> Tuple[Extraction, List[str]]:
    warnings: List[str] = []
    ex = Extraction.model_validate(obj)
    if not ex.service_intent:
        warnings.append("empty_service_intent")
    if ex.service_intent == ["unknown"]:
        ex.raw_extraction_confidence = min(ex.raw_extraction_confidence, 0.5)
    return ex, warnings
