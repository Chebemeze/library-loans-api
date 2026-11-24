"""Exercise the real HTTP handlers with only the service and session replaced."""

import json
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app
from app.services.errors import DomainError

CASES = json.loads(Path(__file__).with_name("member6_cases.json").read_text())


@pytest.fixture
def client():
    app.dependency_overrides[get_session] = lambda: "test-session"
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[get_session]


@pytest.mark.parametrize("method,url,module,name,body,status,result,location", CASES)
def test_dispatch(client, method, url, module, name, body, status, result, location):
    group = url.split("/")[2]
    service = Mock(return_value=result)
    with patch(f"app.routers.{group}.resolve", return_value=service) as resolver:
        response = client.request(method, url, json=body) if body else client.request(method, url)
    assert response.status_code == status, response.text
    assert response.json() == result
    assert response.headers.get("Location") == location
    resolver.assert_called_once_with(module, name)
    segments = url.strip("/").split("/")
    positional = ["test-session"]
    if len(segments) >= 3:
        raw = segments[2]
        positional.append(
            UUID(raw) if group == "members" else int(raw) if group in {"loans", "fines"} else raw
        )
    kws = dict(body or {})
    if "member_id" in kws:
        kws["member_id"] = UUID(kws["member_id"])
    if name in {"search_books", "list_member_loans", "list_member_fines"}:
        kws.update(limit=20, offset=0)
        kws[
            {
                "search_books": "search",
                "list_member_loans": "open_only",
                "list_member_fines": "unpaid",
            }[name]
        ] = None
    service.assert_called_once_with(*positional, **kws)


@pytest.mark.parametrize(
    "method,url,body",
    [
        ("GET", "/v1/loans/0", None),
        ("GET", "/v1/books?limit=101", None),
        ("PATCH", "/v1/members/9e017898-2f34-40c3-a1fd-a3ac1fdfa141", {}),
        ("POST", "/v1/fines/1/payments", {"amount_kobo": True}),
        ("POST", "/v1/loans", {"due_at": "tomorrow"}),
    ],
)
def test_validation(client, method, url, body):
    response = client.request(method, url, json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"
    assert response.json()["message"]


@pytest.mark.parametrize("code,status", [("LOAN_NOT_FOUND", 404), ("ALREADY_RETURNED", 409)])
def test_domain_failure(client, code, status):
    service = Mock(side_effect=DomainError(code, "Example failure"))
    with patch("app.routers.loans.resolve", return_value=service):
        response = client.post("/v1/loans/1/return")
    assert response.status_code == status
    assert response.json() == {"code": code, "message": "Example failure"}


def test_mounted_contract(client):
    import yaml

    contract = yaml.safe_load((Path(__file__).parents[1] / "docs/api/openapi.yaml").read_text())
    generated = client.get("/openapi.json").json()

    def inventory(doc):
        return {
            (method, path, op["operationId"]): set(op["responses"])
            for path, ops in doc["paths"].items()
            for method, op in ops.items()
            if method != "parameters"
        }

    assert inventory(generated) == inventory(contract)
