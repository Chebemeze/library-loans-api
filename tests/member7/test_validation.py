"""Member 7 boundary tests: no database or production service implementation required."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.books import BookCreate
from app.schemas.common import Error
from app.schemas.loans import Loan

MEMBER = "fbfb067b-68f6-4f80-905c-26dfcbdc559e"
BOOK = {"isbn": "123456789X", "title": "Example", "authors": ["B", "A"]}
LOAN = dict(
    id=1,
    member_id=MEMBER,
    copy_barcode="C1",
    borrowed_at="2026-01-01T10:00:00+01:00",
    due_at="2026-01-15T10:00:00+01:00",
    returned_at=None,
)


def test_isbn_shape_and_author_order():
    for isbn in ("123456789X", "9780306406157"):
        model = BookCreate.model_validate({**BOOK, "isbn": isbn})
        assert model.isbn == isbn and model.authors == ["B", "A"]


def test_orm_response_is_utc_and_open():
    result = Loan.model_validate(SimpleNamespace(**LOAN)).model_dump(mode="json")
    assert result["borrowed_at"] == "2026-01-01T09:00:00Z"
    assert result["due_at"] == "2026-01-15T09:00:00Z"
    assert "returned_at" in result and result["returned_at"] is None


@pytest.mark.parametrize(
    "change",
    [
        dict(due_at=LOAN["borrowed_at"]),
        dict(returned_at="2025-12-31T12:00:00Z"),
        dict(borrowed_at="2026-01-01T10:00:00"),
    ],
)
def test_invalid_service_timestamps(change):
    with pytest.raises(ValidationError):
        Loan.model_validate({**LOAN, **change})


def test_closed_error_envelope():
    for fields in [
        dict(code="TYPO", message="Example"),
        dict(code="INVALID_INPUT", message="Example", raw_input="private"),
    ]:
        with pytest.raises(ValidationError):
            Error.model_validate(fields)


@pytest.mark.parametrize(
    "method,url,body,hint",
    [
        ("POST", "/v1/books", {**BOOK, "isbn": "978-0306406157"}, "isbn"),
        ("POST", "/v1/books", {**BOOK, "authors": ["A", "A"]}, "authors"),
        ("POST", "/v1/books", {**BOOK, "authors": ["A"] * 21}, "authors"),
        ("POST", "/v1/books", {**BOOK, "title": "   "}, "title"),
        ("POST", "/v1/books/123456789X/copies", {"barcode": "a" * 65}, "barcode"),
        ("POST", "/v1/members", {"name": "Example", "phone": "not a phone"}, "phone"),
        ("PATCH", f"/v1/members/{MEMBER}", {}, "name or phone"),
        ("PATCH", f"/v1/members/{MEMBER}", {"name": None}, "name"),
        (
            "POST",
            "/v1/loans",
            {"member_id": MEMBER, "copy_barcode": "C1", "due_at": "tomorrow"},
            "due_at",
        ),
        ("POST", "/v1/loans", {"member_id": "invalid", "copy_barcode": "C1"}, "member_id"),
        ("POST", "/v1/fines/1/payments", {"amount_kobo": 1.5}, "amount_kobo"),
        ("GET", "/v1/loans/0", None, "path.loan_id"),
        ("GET", "/v1/books?offset=-1", None, "query.offset"),
    ],
)
def test_invalid_request_shape(method, url, body, hint):
    with TestClient(app) as client:
        result = client.request(method, url, json=body)
    assert result.status_code == 422
    error = Error.model_validate(result.json())
    assert error.code == "INVALID_INPUT"
    assert hint in error.message


def test_malformed_json():
    with TestClient(app) as client:
        r = client.post("/v1/books", content=b"{", headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and Error.model_validate(r.json()).code == "INVALID_INPUT"


def test_invalid_service_result_is_not_client_error():
    with patch("app.routers.loans.resolve", return_value=lambda *_: {"id": 1}):
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.get("/v1/loans/1").status_code == 500


def test_all_published_schema_fields_and_required_keys():
    contract = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "docs/api/openapi.yaml").read_text()
    )
    actual = app.openapi()["components"]["schemas"]
    for name, expected in contract["components"]["schemas"].items():
        found = actual[name]
        assert set(found["properties"]) == set(expected["properties"]), name
        assert set(found.get("required", [])) == set(expected.get("required", [])), name
        if expected.get("additionalProperties") is False:
            assert found["additionalProperties"] is False, name
    assert actual["BookCreate"]["properties"]["authors"]["uniqueItems"] is True
    assert actual["MemberUpdate"]["minProperties"] == 1
    assert actual["MemberUpdate"]["properties"]["name"]["type"] == "string"
    assert set(actual["Error"]["properties"]["code"]["enum"]) == set(
        contract["components"]["schemas"]["Error"]["properties"]["code"]["enum"]
    )
