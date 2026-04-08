# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# Hub validation expects at least three registered graders (named child rubrics)
# and each grader score strictly in (0, 1) — not 0.0 and not 1.0.

from __future__ import annotations

from typing import Any

from openenv.core.rubrics.base import Rubric

# Strictly inside (0, 1) for platform checks
_SCORE_PASS = 0.92
_SCORE_FAIL = 0.08


class StructuredTriageRubric(Rubric):
    """Task: successful step returns core triage labels."""

    def forward(self, action: Any, observation: Any) -> float:
        if getattr(observation, "status", "") != "success":
            return _SCORE_FAIL
        cond = (getattr(observation, "condition", "") or "").strip()
        care = (getattr(observation, "care_recommendation", "") or "").strip()
        reason = (getattr(observation, "reason", "") or "").strip()
        if cond and care and reason:
            return _SCORE_PASS
        return _SCORE_FAIL


class GuidanceFieldsRubric(Rubric):
    """Task: urgency and advice populated on successful triage."""

    def forward(self, action: Any, observation: Any) -> float:
        if getattr(observation, "status", "") != "success":
            return _SCORE_FAIL
        u = (getattr(observation, "urgency", "") or "").strip()
        a = (getattr(observation, "advice", "") or "").strip()
        if len(u) >= 8 and len(a) >= 12:
            return _SCORE_PASS
        return _SCORE_FAIL


class SeverityBandRubric(Rubric):
    """Task: severity is one of the expected bands."""

    _OK = frozenset({"low", "medium", "high"})

    def forward(self, action: Any, observation: Any) -> float:
        if getattr(observation, "status", "") != "success":
            return _SCORE_FAIL
        sev = (getattr(observation, "severity", "") or "").strip().lower()
        if sev in self._OK:
            return _SCORE_PASS
        return _SCORE_FAIL


class JanswasthyaMultiTaskRubric(Rubric):
    """Composite grader: three named tasks; reward is their mean (stays in (0, 1))."""

    def __init__(self) -> None:
        super().__init__()
        self.structured_triage = StructuredTriageRubric()
        self.guidance_fields = GuidanceFieldsRubric()
        self.severity_band = SeverityBandRubric()

    def forward(self, action: Any, observation: Any) -> float:
        s0 = self.structured_triage(action, observation)
        s1 = self.guidance_fields(action, observation)
        s2 = self.severity_band(action, observation)
        return (s0 + s1 + s2) / 3.0
