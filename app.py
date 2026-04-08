"""
Janswasthya AI — minimal FastAPI app for Hugging Face Spaces.

Run locally or on Spaces:
    uvicorn app:app --host 0.0.0.0 --port 7860

Dependencies: fastapi, uvicorn, pydantic
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

# =============================================================================
# predict(text) — same behavior as janswasthya_env_environment.JanswasthyaEnvironment
# Optional refactor: move normalize_text + predict to predict.py and add:
#     from predict import predict
# =============================================================================


def normalize_text(text: str) -> str:
    text = text.lower()
    mapping = {
        "bukhar": "fever",
        "khansi": "cough",
        "saans tez": "fast breathing",
        "dast": "diarrhea",
        "sir dard": "headache",
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


def predict(text: str) -> dict[str, Any]:
    """Triage symptom text → structured dict (condition, severity, action, reason, confidence, …)."""
    text = text.lower()

    _red_flag_markers = (
        "bleeding",
        "blood in urine",
        "urine blood",
        "chest pain",
        "unconscious",
        "not responding",
        "severe breathing",
        "difficulty breathing",
        "high fever 104",
        "very high fever",
    )
    if any(marker in text for marker in _red_flag_markers):
        return {
            "condition": "Critical Condition Detected",
            "severity": "high",
            "action": "Immediate medical attention required",
            "urgency": "Immediate medical attention",
            "advice": "Seek emergency care immediately. Do not delay treatment.",
            "confidence": 0.95,
            "confidence_label": "High",
            "reason": "Detected critical symptom (red flag)",
        }

    text = normalize_text(text)

    symptoms: list[str] = []
    if "fever" in text:
        symptoms.append("fever")
    if "cough" in text:
        symptoms.append("cough")
    if "fast breathing" in text:
        symptoms.append("fast breathing")
    if "diarrhea" in text:
        symptoms.append("diarrhea")
    if "headache" in text:
        symptoms.append("headache")

    if "diarrhea" in symptoms:
        condition = "Diarrhea"
        care_action = "Urgent care"
    elif "fever" in symptoms and "cough" in symptoms:
        condition = "Respiratory Infection"
        care_action = "Refer to PHC"
    elif "fever" in symptoms and "headache" in symptoms:
        condition = "Dengue Risk"
        care_action = "Monitor and test"
    else:
        condition = "General Illness"
        care_action = "Basic care"

    severity = "low"
    if "fast breathing" in symptoms:
        severity = "high"
    elif len(symptoms) >= 2:
        severity = "medium"

    if severity == "high":
        urgency = "Immediate medical attention"
    elif severity == "medium":
        urgency = "Visit doctor within 24 hours"
    else:
        urgency = "Home care sufficient"

    confidence = min(1.0, 0.2 * len(symptoms))
    reason = "Detected: " + ", ".join(symptoms) if symptoms else "No specific symptoms matched"

    if confidence > 0.7:
        confidence_label = "High"
    elif confidence > 0.4:
        confidence_label = "Medium"
    else:
        confidence_label = "Low"

    if condition == "Respiratory Infection":
        advice = "Drink warm fluids, take rest, and visit nearest PHC if symptoms worsen"
    elif condition == "Diarrhea":
        advice = "Drink ORS, stay hydrated, and seek care if symptoms worsen"
    elif condition == "Dengue Risk":
        advice = "Monitor temperature, avoid dehydration, and get blood test"
    else:
        advice = "Take rest and monitor symptoms"

    return {
        "condition": condition,
        "severity": severity,
        "action": care_action,
        "urgency": urgency,
        "advice": advice,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "reason": reason,
    }


# =============================================================================
# Pydantic request models (OpenEnv-compatible body)
# =============================================================================


class ActionPayload(BaseModel):
    message: str = Field(..., description="Symptom or query text")


class StepRequest(BaseModel):
    action: ActionPayload


app = FastAPI(title="Janswasthya AI", version="1.0.0")


def _error_step_payload(detail: str, hint: str) -> dict[str, Any]:
    return {
        "observation": {
            "echoed_message": "",
            "message_length": 0,
            "condition": "",
            "severity": "",
            "care_recommendation": "",
            "reason": "",
            "confidence": 0.0,
            "confidence_label": "",
            "urgency": "",
            "advice": "",
            "status": "error",
            "error_detail": detail,
            "info": {"hint": hint},
        },
        "reward": 0,
        "done": False,
    }


@app.get("/")
def root() -> dict[str, str]:
    """HF Spaces health / discovery."""
    return {"service": "janswasthya-ai", "step": "POST /step"}


# =============================================================================
# POST /step — request handling (validate body → call predict → build response)
# =============================================================================


@app.post("/step")
async def step(body: Any = Body(...)) -> JSONResponse:
    """
    Accepts: {"action": {"message": "<symptom>"}}
    Calls: predict(text) with the trimmed message.
    Returns: observation + reward + done (same shape as OpenEnv StepResponse).
    """
    # --- Parse JSON (invalid JSON → error observation, 200) ---
    if body is None or (isinstance(body, dict) and not body):
        return JSONResponse(
            content=_error_step_payload(
                "Empty or missing JSON body",
                'Send JSON: {"action": {"message": "your symptom text"}}',
            )
        )

    if not isinstance(body, dict):
        return JSONResponse(
            content=_error_step_payload(
                "Request body must be a JSON object",
                'Expected: {"action": {"message": "..."}}',
            )
        )

    # --- Validate with Pydantic (invalid shape → error observation) ---
    try:
        req = StepRequest.model_validate(body)
    except ValidationError as e:
        return JSONResponse(
            content=_error_step_payload(
                "Invalid request body",
                hint=json.dumps(e.errors(), ensure_ascii=False)[:500],
            )
        )

    raw_message = req.action.message
    if not isinstance(raw_message, str):
        raw_message = str(raw_message)
    text = raw_message.strip()

    if not text:
        return JSONResponse(
            content=_error_step_payload(
                "Empty message",
                'Provide non-empty action.message, e.g. {"action":{"message":"fever"}}',
            )
        )

    # --- Call triage: predict(text) ---
    try:
        result = predict(text)
    except Exception as e:
        return JSONResponse(
            content=_error_step_payload(
                str(e),
                "predict() raised an exception; check server logs.",
            )
        )

    return JSONResponse(
        content={
            "observation": {
                "echoed_message": text,
                "message_length": len(text),
                "condition": result["condition"],
                "severity": result["severity"],
                "care_recommendation": result["action"],
                "reason": result["reason"],
                "confidence": float(result["confidence"]),
                "confidence_label": str(result.get("confidence_label", "")),
                "urgency": str(result.get("urgency", "")),
                "advice": str(result.get("advice", "")),
                "status": "success",
                "error_detail": "",
                "info": {},
            },
            "reward": 1,
            "done": False,
        }
    )


# =============================================================================
# Hugging Face Spaces / local entry (uvicorn is not imported at module level)
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
