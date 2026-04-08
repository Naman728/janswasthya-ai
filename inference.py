#!/usr/bin/env python3
"""
Janswasthya AI — hackathon inference demo entry point.

Judges: set API_BASE_URL (and optionally MODEL_NAME, HF_TOKEN), then run:
    python inference.py

Requires: pip install requests python-dotenv
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

# Optional: load variables from a local .env file (pip install python-dotenv).
try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None
if _load_dotenv is not None:
    _load_dotenv()


# ---------------------------------------------------------------------------
# 1) Environment variables (read once at startup)
# ---------------------------------------------------------------------------
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
MODEL_NAME = os.environ.get("MODEL_NAME", "janswasthya-ai")
HF_TOKEN = os.environ.get("HF_TOKEN", "dummy-hf-token-for-demo")


def post_step(symptom_text: str) -> dict[str, Any]:
    """
    Call the FastAPI OpenEnv backend POST /step.

    Note: This server expects OpenEnv's StepRequest shape:
        {"action": {"message": "<symptom text>"}}
    A bare {"text": "..."} body would not match the running app's schema.
    """
    url = f"{API_BASE_URL}/step"
    # Payload uses the same structure as Swagger / OpenEnv clients.
    payload = {"action": {"message": symptom_text}}
    headers = {
        "Content-Type": "application/json",
        # Demonstrate env-driven config for judges / future model routing:
        "X-Model-Name": MODEL_NAME,
    }
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> int:
    # -----------------------------------------------------------------------
    # 2) Call backend for demo cases
    # -----------------------------------------------------------------------
    normal_symptom = "bukhar aur khansi ho rahi hai"
    critical_symptom = "bleeding from urine"

    try:
        normal_out = post_step(normal_symptom)
    except Exception as e:
        normal_out = {"error": str(e), "hint": f"Is the server up at {API_BASE_URL}?"}

    try:
        critical_out = post_step(critical_symptom)
    except Exception as e:
        critical_out = {"error": str(e), "hint": f"Is the server up at {API_BASE_URL}?"}

    # -----------------------------------------------------------------------
    # 3) Required judge output format (exact delimiters)
    #     [START] / [END] wrap <normal_case_output> then <critical_case_output>
    # -----------------------------------------------------------------------
    normal_case_output = json.dumps(normal_out, indent=2, ensure_ascii=False)
    critical_case_output = json.dumps(critical_out, indent=2, ensure_ascii=False)

    print("[START]")
    print(normal_case_output)
    print(critical_case_output)
    print("[END]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
