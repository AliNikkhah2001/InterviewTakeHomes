from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import List, Optional, Literal

ServiceIntent = Literal[
    "engine_diagnostic",
    "oil_change",
    "tire_rotation",
    "tire_pressure",
    "battery",
    "brake_service",
    "ac_service",
    "inspection",
    "unknown"
]

class Extraction(BaseModel):
    vin_detected: bool = False
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    year: Optional[int] = Field(default=None, ge=1980, le=2100)
    service_intent: List[ServiceIntent] = Field(default_factory=list)
    urgency: Literal["low", "medium", "high"] = "medium"
    raw_extraction_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    notes: Optional[str] = None

    @field_validator("vehicle_make", "vehicle_model")
    @classmethod
    def normalize_str(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None
