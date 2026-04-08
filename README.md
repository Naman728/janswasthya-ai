---
title: Janswasthya Ai
emoji: 📚
colorFrom: pink
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# JanSwasthya AI (JanSwasthya Env)

An [OpenEnv](https://github.com/meta-pytorch/OpenEnv)-compatible environment that exposes a simple **symptom-to-triage** flow over HTTP. Built for hackathon demos, agents, and RL-style tooling—not clinical diagnosis.

## Hugging Face Space

- **`sdk: docker`** + root **`Dockerfile`** build the OpenEnv FastAPI app; **`app_port: 7860`** matches the proxy. [Spaces configuration reference](https://huggingface.co/docs/hub/spaces-config-reference).
- **Live Space (add your link):** `https://huggingface.co/spaces/<your-username>/<your-space-name>` — use the Space **API base URL** for hackathon checks (e.g. `POST /reset` must return JSON, not HTML).
- Optional **standalone** API: root **`app.py`** with `uvicorn app:app --port 7860` (not used by the root Docker image; the image runs **`server.app:app`** inside `janswasthya_env/`).

### Screenshots

_Add images to your repo and link them here, for example:_

```markdown
![Triage demo](docs/demo-step.png)
```

## Features

- **OpenEnv contract**: `JanswasthyaEnvironment` subclasses OpenEnv’s `Environment`; `reset` and `step` return Pydantic observations (required for `POST /step` to serialize correctly).
- **Hindi → English** normalization for common symptom phrases (e.g. bukhar → fever).
- **Red-flag phrases** (bleeding, chest pain, difficulty breathing, etc.) map to a critical triage response before normal rules run.
- **Structured outputs** from `predict()`: condition, severity, care recommendation, urgency, advice, confidence, and labels.

## Requirements

- Python **3.10+**
- Dependencies are declared in `janswasthya_env/pyproject.toml` (`openenv-core[core]>=0.2.2`, etc.).

## Install

From the environment package directory:

```bash
cd janswasthya_env
uv sync
```

Or install in editable mode:

```bash
cd janswasthya_env
pip install -e .
```

Optional root-level install using `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Run the server (OpenEnv)

```bash
cd janswasthya_env
uv run server
# or
uv run --project . python -m janswasthya_env.server.app
# or
uvicorn janswasthya_env.server.app:app --host 0.0.0.0 --port 8000
```

Default port in `openenv.yaml` is **8000**. Interactive docs: `http://localhost:8000/docs`.

## Hackathon: environment variables

- **`OPENENV_BASE_URL`** — Base URL of **your** OpenEnv FastAPI app (`POST /step`, `POST /reset`). Local default: `http://127.0.0.1:8000`.
- **`API_BASE_URL`** + **`API_KEY`** — Injected **LiteLLM / OpenAI-compatible proxy** (use with the official `openai` client only). Do not point these at your own `/step` server.
- **`MODEL_NAME`** — Chat model id for the proxy (e.g. `gpt-4o-mini`).

`inference.py` and root `app.py` perform a minimal proxy chat call when `API_BASE_URL` and `API_KEY` are set, so automated checks can observe traffic on the provided key.

## Hackathon demo script

From the repo root (OpenEnv running, optional `.env` from `.env.example`):

```bash
pip install -r requirements.txt
python inference.py
```

Output is wrapped in `[START]` / `[END]` for judge scripts.

## API quick reference

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/reset` | Reset episode; returns initial observation |
| `POST` | `/step` | Send an action; returns observation, reward, done |

**Step request body** (OpenEnv shape):

```json
{
  "action": {
    "message": "bukhar and khansi"
  }
}
```

**Step response** (top-level keys from OpenEnv):

- `observation` — fields from `JanswasthyaObservation` (e.g. `condition`, `severity`, `care_recommendation`, `urgency`, `advice`, `confidence`, `confidence_label`, `echoed_message`, `status`, `info`, …)
- `reward`
- `done`

Other routes (state, schema, WebSocket, etc.) follow the standard OpenEnv FastAPI app.

## Project layout

```
JanSwasthyaEnv/
├── README.md
├── app.py                 # Standalone FastAPI (e.g. HF Spaces)
├── inference.py           # Judge / demo client
├── requirements.txt
└── janswasthya_env/
    ├── pyproject.toml
    ├── openenv.yaml       # OpenEnv spec (app entry, port)
    ├── models.py          # JanswasthyaAction / JanswasthyaObservation
    └── server/
        ├── app.py         # OpenEnv create_app(...)
        ├── janswasthya_env_environment.py
        └── Dockerfile
```

## Docker

`janswasthya_env/server/Dockerfile` targets the OpenEnv base image and builds the environment with `uv`. Use the OpenEnv CLI’s build flow when packaging (`openenv build`), or build with your chosen context from that directory.

## Medical disclaimer

This project uses **rule-based heuristics** for demonstration only. It is **not** a substitute for professional medical advice, diagnosis, or emergency services.

## License

See the license headers in source files (BSD-style per upstream OpenEnv template where applicable).
