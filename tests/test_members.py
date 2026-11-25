"""Members: registration, edits, suspension.

The interesting part is the PATCH contract: omitted stays unchanged, ``phone:
null`` clears, ``name: null`` is rejected, and whitespace is not a value.
"""

from __future__ import annotations

import uuid
from typing import Any

from helpers import assert_error, assert_only


def test_create_member_returns_only_the_uuid(client: Any) -> None:
    response = client.post("/v1/members", json={"name": "Ada Nwosu"})

    assert response.status_code == 201, response.text
    assert_only(response.json(), {"id"})
    assert uuid.UUID(str(response.json()["id"]))


def test_member_starts_active_with_no_phone(client: Any, make_member: Any) -> None:
    member_id = make_member(name="Ada Nwosu")

    body = client.get(f"/v1/members/{member_id}").json()

    assert body == {"id": member_id, "name": "Ada Nwosu", "phone": None, "status": "active"}


def test_phone_must_be_digits_with_optional_plus(client: Any) -> None:
    assert client.post(
        "/v1/members", json={"name": "Ada", "phone": "0803 123 4567"}
    ).status_code == 422
    assert client.post("/v1/members", json={"name": "Ada", "phone": "123"}).status_code == 422
    assert client.post(
        "/v1/members", json={"name": "Ada", "phone": "+2348031234567"}
    ).status_code == 201


def test_patch_keeps_omitted_fields(client: Any, make_member: Any) -> None:
    member_id = make_member(phone="+2348031234567")

    body = client.patch(f"/v1/members/{member_id}", json={"name": "Ada Okafor"}).json()

    assert body["name"] == "Ada Okafor"
    assert body["phone"] == "+2348031234567"


def test_patch_phone_null_clears_it(client: Any, make_member: Any) -> None:
    member_id = make_member(phone="+2348031234567")

    body = client.patch(f"/v1/members/{member_id}", json={"phone": None}).json()

    assert body["phone"] is None
    assert client.get(f"/v1/members/{member_id}").json()["phone"] is None


def test_patch_rejects_empty_body_null_name_and_blank_name(
    client: Any, make_member: Any
) -> None:
    member_id = make_member()

    assert client.patch(f"/v1/members/{member_id}", json={}).status_code == 422
    assert client.patch(f"/v1/members/{member_id}", json={"name": None}).status_code == 422
    assert client.patch(f"/v1/members/{member_id}", json={"name": "   "}).status_code == 422


def test_suspend_then_reactivate(client: Any, make_member: Any) -> None:
    member_id = make_member()

    suspended = client.post(f"/v1/members/{member_id}/suspend")
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["status"] == "suspended"

    reactivated = client.post(f"/v1/members/{member_id}/reactivate")
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "active"


def test_suspend_twice_is_409_and_reactivate_twice_is_409(
    client: Any, make_member: Any
) -> None:
    member_id = make_member()

    client.post(f"/v1/members/{member_id}/suspend")
    assert_error(client.post(f"/v1/members/{member_id}/suspend"), 409, "ALREADY_SUSPENDED")

    client.post(f"/v1/members/{member_id}/reactivate")
    assert_error(client.post(f"/v1/members/{member_id}/reactivate"), 409, "NOT_SUSPENDED")


def test_unknown_member_is_404_everywhere(client: Any) -> None:
    missing = str(uuid.uuid4())

    assert_error(client.get(f"/v1/members/{missing}"), 404, "MEMBER_NOT_FOUND")
    patched = client.patch(f"/v1/members/{missing}", json={"name": "X"})
    assert_error(patched, 404, "MEMBER_NOT_FOUND")
    assert_error(client.post(f"/v1/members/{missing}/suspend"), 404, "MEMBER_NOT_FOUND")
    assert_error(client.post(f"/v1/members/{missing}/reactivate"), 404, "MEMBER_NOT_FOUND")
    assert_error(client.get(f"/v1/members/{missing}/loans"), 404, "MEMBER_NOT_FOUND")
    assert_error(client.get(f"/v1/members/{missing}/fines"), 404, "MEMBER_NOT_FOUND")


def test_member_id_must_be_a_uuid(client: Any) -> None:
    assert client.get("/v1/members/not-a-uuid").status_code == 422
