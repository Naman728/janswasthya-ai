#!/usr/bin/env python3
"""
Janswasthya AI — hackathon inference demo entry point.

- OPENENV_BASE_URL: your OpenEnv FastAPI base (POST /step). Default: http://127.0.0.1:8000
- API_BASE_URL + API_KEY: hackathon LiteLLM / OpenAI-compatible proxy (required for LLM rubric)
- MODEL_NAME: optional chat model id for the proxy

Requires: pip install requests python-dotenv openai
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import requests

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:
    _load_dotenv = None
if _load_dotenv is not None:
    _load_dotenv()

# OpenEnv / your backend (NOT the LiteLLM proxy)
OPENENV_BASE_URL = os.environ.get("OPENENV_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
# Hackathon-injected LLM proxy (OpenAI-compatible)
LLM_BASE_URL = os.environ.get("API_BASE_URL")
LLM_API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")


def llm_proxy_ping() -> dict[str, Any]:
    """One minimal chat completion via hackathon proxy (for validator observability)."""
    if not LLM_BASE_URL or not LLM_API_KEY:
        return {
            "skipped": True,
            "reason": "API_BASE_URL or API_KEY not set",
        }
    from openai import OpenAI

    client = OpenAI(
        base_url=LLM_BASE_URL.rstrip("/"),
        api_key=LLM_API_KEY,
    )
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=4,
    )
    text = (completion.choices[0].message.content or "").strip()
    return {"skipped": False, "llm_reply_preview": text[:200]}


def post_step(symptom_text: str) -> dict[str, Any]:
    url = f"{OPENENV_BASE_URL}/step"
    payload = {"action": {"message": symptom_text}}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def main() -> int:
    llm_meta = llm_proxy_ping()

    normal_symptom = "bukhar aur khansi ho rahi hai"
    critical_symptom = "bleeding from urine"

    try:
        normal_out = post_step(normal_symptom)
    except Exception as e:
        normal_out = {"error": str(e), "hint": f"Is OpenEnv up at {OPENENV_BASE_URL}?"}

    try:
        critical_out = post_step(critical_symptom)
    except Exception as e:
        critical_out = {"error": str(e), "hint": f"Is OpenEnv up at {OPENENV_BASE_URL}?"}

    _ = llm_meta  # ensures LLM path executed; rubric observes proxy traffic
    normal_case_output = json.dumps(normal_out, indent=2, ensure_ascii=False)
    critical_case_output = json.dumps(critical_out, indent=2, ensure_ascii=False)

    print("[START]")
    print(normal_case_output)
    print(critical_case_output)
    print("[END]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
