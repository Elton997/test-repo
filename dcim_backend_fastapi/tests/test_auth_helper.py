from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException, status

from app.core.config import settings
from app.helpers import auth_helper


class DummyRole:
    def __init__(self, code: str | None, is_active: bool = True) -> None:
        self.code = code
        self.is_active = is_active


class DummyUserRole:
    def __init__(self, role: DummyRole | None) -> None:
        self.role = role


class DummyUser:
    def __init__(
        self,
        *,
        user_id: int = 1,
        name: str = "jdoe",
        email: str = "jdoe@example.com",
        is_active: bool = True,
        roles: list[DummyUserRole] | None = None,
    ) -> None:
        self.id = user_id
        self.name = name
        self.email = email
        self.is_active = is_active
        self.user_roles = roles or []


def test_get_token_from_header_valid():
    token = "abc123"
    header = f"Bearer {token}"

    result = auth_helper._get_token_from_header(header)  # type: ignore[attr-defined]

    assert result == token


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "Token abc",
        "Bearer ",
        "bearer",  # missing token part
    ],
)
def test_get_token_from_header_invalid(header):
    with pytest.raises(HTTPException) as exc_info:
        auth_helper._get_token_from_header(header)  # type: ignore[attr-defined]

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_build_jwt_payload_includes_roles_and_expiry():
    roles = [
        DummyUserRole(DummyRole("admin", is_active=True)),
        DummyUserRole(DummyRole("viewer", is_active=False)),  # inactive ignored
        DummyUserRole(DummyRole(None, is_active=True)),  # no code ignored
    ]
    user = DummyUser(user_id=42, roles=roles)

    payload = auth_helper._build_jwt_payload(user)  # type: ignore[attr-defined]

    assert payload["sub"] == str(42)
    assert payload["username"] == user.name
    assert payload["email"] == user.email
    # Only ADMIN should be present and upper-cased
    assert payload["roles"] == ["ADMIN"]
    assert payload["is_active"] is True

    now = datetime.now(timezone.utc).timestamp()
    assert payload["iat"] <= int(now)
    assert payload["exp"] > payload["iat"]


def test_create_and_decode_access_token_roundtrip():
    user = DummyUser(user_id=7)

    token = auth_helper.create_access_token_for_user(user=user)
    assert isinstance(token, str) and token

    decoded = auth_helper.decode_access_token(token)

    assert decoded["sub"] == str(7)
    assert decoded["username"] == user.name


def test_decode_access_token_expired_raises_419():
    payload = {
        "sub": "1",
        "exp": int((datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp()),
    }
    expired_token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_helper.decode_access_token(expired_token)

    assert exc_info.value.status_code == 419
    assert "expired" in exc_info.value.detail.lower()


def test_decode_access_token_invalid_signature_raises_401():
    # Token signed with a different key should be rejected
    bogus_token = jwt.encode(
        {"sub": "1"},
        "wrong-key",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_helper.decode_access_token(bogus_token)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid" in exc_info.value.detail.lower()


