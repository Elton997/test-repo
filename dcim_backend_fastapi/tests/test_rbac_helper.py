from fastapi import HTTPException, status

from app.helpers import rbac_helper


def test_access_level_from_roles_priority_admin_over_editor():
    roles = {"ADMIN", "EDITOR", "VIEWER"}

    level = rbac_helper._access_level_from_roles(roles)  # type: ignore[attr-defined]

    assert level is rbac_helper.AccessLevel.admin


def test_access_level_from_roles_editor_when_no_admin():
    roles = {"editor"}

    level = rbac_helper._access_level_from_roles({r.upper() for r in roles})  # type: ignore[attr-defined]

    assert level is rbac_helper.AccessLevel.editor


def test_access_level_from_roles_viewer_default():
    level = rbac_helper._access_level_from_roles(set())  # type: ignore[attr-defined]

    assert level is rbac_helper.AccessLevel.viewer


def _make_jwt(roles, is_superuser: bool = False) -> str:
    from app.core.config import settings
    import jwt

    payload = {
        "sub": "1",
        "username": "jdoe",
        "roles": roles,
    }
    if is_superuser:
        payload["is_superuser"] = True

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_get_access_level_uses_roles_from_jwt():
    token = _make_jwt(["viewer"])
    header = f"Bearer {token}"

    level = rbac_helper.get_access_level(authorization=header)

    assert level is rbac_helper.AccessLevel.viewer


def test_get_access_level_treats_superuser_as_admin():
    token = _make_jwt(["viewer"], is_superuser=True)
    header = f"Bearer {token}"

    level = rbac_helper.get_access_level(authorization=header)

    assert level is rbac_helper.AccessLevel.admin


def test_require_editor_or_admin_allows_editor():
    result = rbac_helper.require_editor_or_admin(
        access_level=rbac_helper.AccessLevel.editor
    )

    assert result is rbac_helper.AccessLevel.editor


def test_require_editor_or_admin_blocks_viewer():
    try:
        rbac_helper.require_editor_or_admin(
            access_level=rbac_helper.AccessLevel.viewer
        )
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert "editor or admin" in exc.detail
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected HTTPException for viewer access")


def test_require_admin_only_allows_admin():
    result = rbac_helper.require_admin(access_level=rbac_helper.AccessLevel.admin)

    assert result is rbac_helper.AccessLevel.admin


def test_require_admin_raises_for_non_admin():
    for level in (
        rbac_helper.AccessLevel.viewer,
        rbac_helper.AccessLevel.editor,
    ):
        try:
            rbac_helper.require_admin(access_level=level)
        except HTTPException as exc:
            assert exc.status_code == status.HTTP_403_FORBIDDEN
            assert "Admin access required" in exc.detail
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected HTTPException for non-admin access")


