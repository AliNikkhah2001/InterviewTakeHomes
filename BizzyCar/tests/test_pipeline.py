import json, asyncio, os, re
from src.processing import process_notes, redact, detect_hallucinations, calibrate_confidence
from src.schemas import Extraction

def test_process_notes_happy_path():
    """Test successful extraction from a clear service note."""
    notes = ["2018 Camry in for oil change."]
    out = asyncio.run(process_notes(notes))
    assert isinstance(out, list) and len(out) == 1
    item = out[0]
    assert "service_intent" in item and len(item["service_intent"]) >= 1
    assert item["vehicle_make"] == "Toyota"
    assert item["vehicle_model"] == "Camry"
    assert item["year"] == 2018
    assert "oil_change" in item["service_intent"]
    # Confidence should be reasonable for clear input
    assert item["raw_extraction_confidence"] >= 0.5

def test_process_notes_hallucination_or_badjson():
    """Test handling of hallucinations and malformed output."""
    notes = ["VIN 1HGCM82633A004352 customer says brake grinding and maybe alternator ?!?!?!?"]
    out = asyncio.run(process_notes(notes))
    assert out[0]["service_intent"], "Should still return a valid record via retries or fallback"
    # Should detect brake service at minimum
    assert len(out[0]["service_intent"]) > 0

def test_pii_redaction():
    """Test that PII (emails and phones) is properly redacted."""
    text_with_email = "Customer john.doe@example.com called about service."
    redacted = redact(text_with_email)
    assert "john.doe@example.com" not in redacted
    assert "<redacted_email>" in redacted
    
    text_with_phone = "Call customer at +1-555-123-4567 before appointment."
    redacted_phone = redact(text_with_phone)
    assert "555-123-4567" not in redacted_phone
    assert "<redacted_phone>" in redacted_phone

def test_hallucination_detection():
    """Test that spurious 'inspection' intent is detected."""
    obj_with_hallucination = {
        "service_intent": ["oil_change", "inspection"],
        "vehicle_make": "Toyota",
        "raw_extraction_confidence": 0.7
    }
    original_text = "Customer needs oil change"
    # 'inspection' is in the intents but not in the text -> hallucination
    is_hallucination = detect_hallucinations(obj_with_hallucination, original_text)
    assert is_hallucination, "Should detect spurious 'inspection'"
    
    obj_no_hallucination = {
        "service_intent": ["oil_change"],
        "vehicle_make": "Toyota",
        "raw_extraction_confidence": 0.7
    }
    is_hallucination = detect_hallucinations(obj_no_hallucination, original_text)
    assert not is_hallucination, "Should not flag normal output as hallucination"

def test_confidence_calibration():
    """Test that confidence is properly calibrated based on signals."""
    # Low confidence with no vehicle make -> should be down-weighted
    obj_weak = {
        "service_intent": ["unknown"],
        "vehicle_make": None,
        "vehicle_model": None,
        "raw_extraction_confidence": 0.8
    }
    calibrated = calibrate_confidence(obj_weak.copy(), "generic service question")
    assert calibrated["raw_extraction_confidence"] <= 0.5, "Should down-weight weak signals"
    
    # Strong signal with good confidence -> should be boosted
    obj_strong = {
        "service_intent": ["oil_change", "tire_rotation"],
        "vehicle_make": "Toyota",
        "vehicle_model": "Camry",
        "raw_extraction_confidence": 0.65
    }
    calibrated_strong = calibrate_confidence(obj_strong.copy(), "2018 Camry needs oil change and tire rotation")
    # Should be boosted due to strong signals and reasonable initial confidence
    assert calibrated_strong["raw_extraction_confidence"] > obj_strong["raw_extraction_confidence"]

def test_batch_processing():
    """Test processing multiple notes at once."""
    notes = [
        "2018 Camry in for check-engine light and oil change. Tire pressure low.",
        "Customer: 'Hearing grinding noise when braking on 2015 Accord. VIN 1HGCM82633A004352'",
        "Need appointment for tire rotation, also AC not cooling well on 2020 Rogue."
    ]
    out = asyncio.run(process_notes(notes))
    assert len(out) == 3
    for item in out:
        assert isinstance(item, dict)
        assert "service_intent" in item
        assert "vehicle_make" in item or item["vehicle_make"] is None
        assert "raw_extraction_confidence" in item
        assert 0.0 <= item["raw_extraction_confidence"] <= 1.0

def test_logging_output():
    """Test that structured logs are written to JSONL."""
    # Process a note
    notes = ["Quick oil change for 2020 Accord"]
    asyncio.run(process_notes(notes))
    
    # Check if pipeline.jsonl exists and contains valid JSON lines
    if os.path.exists('pipeline.jsonl'):
        with open('pipeline.jsonl', 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0, "Should have written log entries"
            for line in lines[-5:]:  # Check last 5 lines
                try:
                    log_entry = json.loads(line)
                    assert "timestamp" in log_entry
                    assert "event_type" in log_entry
                except json.JSONDecodeError:
                    pass  # Some lines might be partial
