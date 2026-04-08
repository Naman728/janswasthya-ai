# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Janswasthya triage-style environment.

OpenEnv contract (see openenv.core.env_server.interfaces.Environment):
- reset(...) -> JanswasthyaObservation (Pydantic Observation subclass)
- step(action: JanswasthyaAction, ...) -> JanswasthyaObservation
- state -> State

HTTP POST /step sends JSON like {"action": {"message": "..."}}; the server deserializes
`action` into JanswasthyaAction before calling step(). Returning a plain dict causes 500s
because serialize_observation() expects an Observation instance.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import JanswasthyaAction, JanswasthyaObservation
    from .janswasthya_rubrics import JanswasthyaMultiTaskRubric
except ImportError:
    from models import JanswasthyaAction, JanswasthyaObservation
    from server.janswasthya_rubrics import JanswasthyaMultiTaskRubric


class JanswasthyaEnvironment(Environment[JanswasthyaAction, JanswasthyaObservation, State]):
    """Triage environment: message in, structured observation out."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self) -> None:
        super().__init__(rubric=JanswasthyaMultiTaskRubric())
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def _finalize_observation(
        self, action: JanswasthyaAction, obs: JanswasthyaObservation
    ) -> JanswasthyaObservation:
        """Set reward from registered rubrics (scores must stay strictly inside (0, 1))."""
        obs.reward = self._apply_rubric(action, obs)
        return self._apply_transform(obs)

    def normalize_text(self, text: str) -> str:
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

    def predict(self, text: str) -> dict[str, Any]:
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

        text = self.normalize_text(text)

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

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> JanswasthyaObservation:
        self._reset_rubric()
        self._state = State(episode_id=str(uuid4()), step_count=0)

        return JanswasthyaObservation(
            echoed_message="Janswasthya environment ready.",
            message_length=0,
            done=False,
            reward=0.5,
            info={},
        )

    def step(
        self,
        action: JanswasthyaAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> JanswasthyaObservation:
        """
        Run triage on `action.message`. The HTTP layer already parsed nested JSON into JanswasthyaAction.

        On failure, returns a valid observation with status=error (no exception) so the server returns 200.
        """
        raw_message = ""
        try:
            raw_message = action.message if action.message is not None else ""
            if not isinstance(raw_message, str):
                raw_message = str(raw_message)
            text = raw_message.strip()

            if not text:
                empty_obs = JanswasthyaObservation(
                    echoed_message="",
                    message_length=0,
                    done=False,
                    reward=0.5,
                    urgency="",
                    advice="",
                    confidence_label="",
                    status="error",
                    error_detail="Empty message: provide action.message",
                    info={"hint": 'Send {"action": {"message": "your symptom text"}}'},
                )
                return self._finalize_observation(action, empty_obs)

            self._state.step_count += 1
            result = self.predict(text)

            obs = JanswasthyaObservation(
                echoed_message=text,
                message_length=len(text),
                condition=result["condition"],
                severity=result["severity"],
                care_recommendation=result["action"],
                reason=result["reason"],
                confidence=float(result["confidence"]),
                confidence_label=str(result.get("confidence_label", "")),
                urgency=str(result.get("urgency", "")),
                advice=str(result.get("advice", "")),
                done=False,
                reward=0.5,
                status="success",
                error_detail="",
                info={},
            )
            return self._finalize_observation(action, obs)

        except Exception as e:
            err_obs = JanswasthyaObservation(
                echoed_message=raw_message,
                message_length=len(raw_message),
                done=False,
                reward=0.5,
                urgency="",
                advice="",
                confidence_label="",
                status="error",
                error_detail=str(e),
                info={"exception_type": type(e).__name__},
            )
            return self._finalize_observation(action, err_obs)

    @property
    def state(self) -> State:
        return self._state
