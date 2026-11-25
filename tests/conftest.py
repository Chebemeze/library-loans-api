"""Fixtures for the Library Loans API test suite.

Owner: Member 2 (test harness + release evidence).
The tests are black-box: they speak HTTP to the ASGI app and read the database
directly, but never import routers, services or repositories.

Three things here are deliberate and easy to break:

1. ``DATABASE_URL`` is rewritten to the test database *before* ``app`` is
   imported. ``app/db/session.py`` creates the engine at import time, and
   ``app/config.py`` sets ``extra="ignore"``, so a ``TEST_DATABASE_URL``
   setting does not exist -- it is silently dropped. Exporting it alone does
   nothing.

2. The schema is built with ``alembic upgrade head``, never ``create_all()``,
   so a broken migration fails the suite instead of being masked by the ORM.

3. The database is truncated between tests, not rolled back. The app commits
   inside each request, so a transaction-per-test would not isolate anything.
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _read_env_file() -> dict[str, str]:
    """Read ``.env`` without importing the app's settings loader."""
    path = ROOT / ".env"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


ENV_FILE = _read_env_file()
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or ENV_FILE.get("TEST_DATABASE_URL", "")
DEV_DATABASE_URL = os.environ.get("DATABASE_URL") or ENV_FILE.get("DATABASE_URL", "")

def pytest_configure(config: pytest.Config) -> None:
    if not TEST_DATABASE_URL:
        raise pytest.UsageError(
            "TEST_DATABASE_URL is not set, so the suite cannot pick a database. "
            "Add it to .env (see .env.example) or pass it inline:\n"
            '  TEST_DATABASE_URL="postgresql+psycopg://gamp:gamp@127.0.0.1:5432/'
            'library_test" uv run pytest'
        )

    if TEST_DATABASE_URL == DEV_DATABASE_URL:
        raise pytest.UsageError(
            "TEST_DATABASE_URL and DATABASE_URL are the same database. The suite "
            "truncates every table between tests, so it refuses to run against the "
            "development database. Point TEST_DATABASE_URL at a separate database "
            "(library_test in .env.example)."
        )


# Must happen before `import app` anywhere in the process: app/db/session.py
# builds the engine at import time from this value.
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL


# --------------------------------------------------------------------------- #
# session-scoped setup: app, schema, engine
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def app() -> Any:
    """The ASGI application under test."""
    try:
        from app.main import app as asgi_app
    except ModuleNotFoundError as exc:
        pytest.exit(
            f"app.main is not importable yet: {exc}\n\n"
            "The suite is written from docs/api/openapi.yaml and needs an "
            "importable FastAPI object at app/main.py (`app = FastAPI(...)`) "
            "before anything can run. Land that file, then re-run.",
            returncode=2,
        )
    return asgi_app


@pytest.fixture(scope="session")
def engine(app: Any) -> Iterator[Any]:
    """The engine the app itself built, checked to be pointed at the test DB."""
    from sqlalchemy.engine import make_url

    from app.db.session import engine as app_engine

    bound = make_url(str(app_engine.url)).database or ""
    expected = make_url(TEST_DATABASE_URL).database or ""

    if bound != expected:
        raise pytest.UsageError(
            f"the app is connected to {bound!r}, not {expected!r}. "
            "Something imported app.db.session before conftest rewrote DATABASE_URL."
        )

    if "test" not in bound:
        raise pytest.UsageError(
            f"refusing to run: database {bound!r} does not look like a test "
            "database, and every table is truncated between tests."
        )

    yield app_engine
    app_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Build the schema the way production builds it."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session", autouse=True)
def contract_settings(migrated_database: None) -> None:
    """Fail loudly if .env overrides the rules the tests assert."""
    from app.config import get_settings

    settings = get_settings()
    actual = (
        settings.loan_period_days,
        settings.loan_limit_per_member,
        settings.fine_per_late_day_kobo,
        settings.fine_cap_per_loan_kobo,
    )
    if actual != (14, 3, 50, 2000):
        raise pytest.UsageError(
            f"business rules are {actual}, but docs/api/openapi.yaml and this "
            "suite assert (14 days, 3 loans, 50 kobo/day, 2000 kobo cap). "
            "Either fix .env or update both together."
        )


@pytest.fixture(autouse=True)
def clean_database(engine: Any) -> None:
    """Empty every table before each test, keeping identities predictable."""
    from sqlalchemy import text

    import app.db.models  # noqa: F401  # register the tables
    from app.db.base import Base

    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


# --------------------------------------------------------------------------- #
# clients and raw database access
# --------------------------------------------------------------------------- #


@pytest.fixture
def client(app: Any) -> Iterator[Any]:
    """HTTP client that runs the app's lifespan and raises on unhandled errors."""
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def raw_client(app: Any) -> Iterator[Any]:
    """Same client, but a 500 becomes a response instead of an exception.

    Needed by test_atomicity, where the point is *that* the request failed.
    """
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def db(engine: Any, clean_database: None) -> Iterator[Any]:
    """A connection for reading and setting up rows the API cannot reach."""
    with engine.connect() as connection:
        yield connection
        connection.rollback()


@pytest.fixture
def anyio_backend() -> str:
    """anyio ships with starlette, so the race tests need no extra dependency."""
    return "asyncio"


# --------------------------------------------------------------------------- #
# factories
# --------------------------------------------------------------------------- #


def _unique_isbn() -> str:
    """A 13-digit ISBN-shaped value. The API validates the pattern, not the check digit."""
    return "978" + f"{uuid.uuid4().int % 10**10:010d}"


@pytest.fixture
def make_book(client: Any) -> Callable[..., str]:
    def _make_book(
        isbn: str | None = None,
        title: str = "The Long Afternoon",
        authors: tuple[str, ...] = ("Ada Nwosu",),
    ) -> str:
        new_isbn = isbn or _unique_isbn()
        payload = {"isbn": new_isbn, "title": title, "authors": list(authors)}
        response = client.post("/v1/books", json=payload)
        assert response.status_code == 201, response.text
        return new_isbn

    return _make_book


@pytest.fixture
def make_copy(client: Any) -> Callable[..., str]:
    def _make_copy(isbn: str, barcode: str | None = None) -> str:
        barcode = barcode or "BC-" + uuid.uuid4().hex[:12]
        response = client.post(f"/v1/books/{isbn}/copies", json={"barcode": barcode})
        assert response.status_code == 201, response.text
        return barcode

    return _make_copy


@pytest.fixture
def make_member(client: Any) -> Callable[..., str]:
    def _make_member(name: str = "Ada Nwosu", phone: str | None = None) -> str:
        payload: dict[str, Any] = {"name": name}
        if phone is not None:
            payload["phone"] = phone
        response = client.post("/v1/members", json=payload)
        assert response.status_code == 201, response.text
        return str(response.json()["id"])

    return _make_member


@pytest.fixture
def borrow(client: Any) -> Callable[..., dict[str, Any]]:
    """Borrow a free copy and return the created loan body."""

    def _borrow(copy_barcode: str, member_id: str) -> dict[str, Any]:
        response = client.post(
            "/v1/loans", json={"copy_barcode": copy_barcode, "member_id": member_id}
        )
        assert response.status_code == 201, response.text
        return dict(response.json())

    return _borrow


@pytest.fixture
def post_loan(client: Any) -> Callable[..., Any]:
    """Attempt a borrow without asserting the outcome (for conflict tests)."""

    def _post_loan(copy_barcode: str, member_id: str) -> Any:
        return client.post(
            "/v1/loans", json={"copy_barcode": copy_barcode, "member_id": member_id}
        )

    return _post_loan
