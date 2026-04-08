# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Janswasthya Env Environment.

Symptom text in; triage-style observation fields out (OpenEnv serializes these into POST /step).
"""

from typing import Any, Dict

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class JanswasthyaAction(Action):
    """Action for the Janswasthya Env environment — user symptom or query text."""

    message: str = Field(..., description="Symptom or query text")


class JanswasthyaObservation(Observation):
    """Observation: echoed input plus triage fields (serialized into the `observation` object on /step)."""

    echoed_message: str = Field(default="", description="Input message after processing")
    message_length: int = Field(default=0, description="Length of input message")
    condition: str = Field(default="", description="Inferred condition label")
    severity: str = Field(default="", description="low | medium | high")
    care_recommendation: str = Field(
        default="", description="Suggested care / referral (from triage logic)"
    )
    reason: str = Field(default="", description="Short rationale")
    confidence: float = Field(default=0.0, description="Model confidence score")
    confidence_label: str = Field(
        default="", description="Human-readable confidence band (High | Medium | Low)"
    )
    urgency: str = Field(
        default="", description="How quickly to seek care (e.g. immediate vs home care)"
    )
    advice: str = Field(default="", description="Plain-language self-care / referral guidance")
    status: str = Field(default="success", description="success or error")
    error_detail: str = Field(default="", description="Populated when status is error")
    info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extra structured info (surfaced inside observation; OpenEnv has no top-level info field)",
    )
