"""Health probes. Unversioned, so they must not drift with the API version."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from helpers import ERROR_CODES

ROOT = Path(__file__).resolve().parents[1]


def test_ready_reports_ready_when_the_database_answers(client: Any) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ready"}


def test_ready_is_503_when_the_database_is_unreachable() -> None:
    """Run the app in a subprocess against a closed port: the real database
    cannot be dropped mid-session, and patching the engine tests the patch."""
    script = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "with TestClient(app, raise_server_exceptions=False) as client:\n"
        "    response = client.get('/health/ready')\n"
        "    body = response.json()\n"
        "    assert response.status_code == 503, (response.status_code, body)\n"
        "    assert set(body) == {'code', 'message'}, body\n"
        "    assert body['code'] in "
        f"{sorted(ERROR_CODES)!r}, body\n"
        "    assert body['code'] == 'DATABASE_UNAVAILABLE', body\n"
        "print('ok')\n"
    )
    env = os.environ | {
        "DATABASE_URL": "postgresql+psycopg://nobody:nobody@127.0.0.1:1/library_test",
    }

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
