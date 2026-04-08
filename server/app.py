# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# Repo-root entrypoint expected by openenv validate (server/app.py).
# Implementation stays in janswasthya_env/server/app.py.

from janswasthya_env.server.app import app

__all__ = ["app"]


def main() -> None:
    """Run the API (local / validate). Docker/HF use: uvicorn server.app:app --port 7860."""
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
