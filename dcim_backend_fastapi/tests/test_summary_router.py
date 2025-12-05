import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.helpers.auth_helper import get_current_user
from app.helpers.rbac_helper import require_at_least_viewer


class DummyAccessLevel:
    def __init__(self, value: str = "viewer") -> None:
        self.value = value


class DummyUser:
    def __init__(self, user_id: int = 1) -> None:
        self.id = user_id


@pytest.fixture
def client():
    """
    TestClient for /api/dcim/summary/locations with DB, auth and RBAC overridden.
    """
    # Disable DB prewarm during app lifespan to avoid requiring real DB_URL
    import app.main as main_module

    async def _noop_prewarm(app_logger):  # type: ignore[unused-argument]
        return None

    main_module._prewarm_database = _noop_prewarm  # type: ignore[assignment]
    class DummyDB:
        def __init__(self, rows=None) -> None:
            self.rows = rows or []

    dummy_db = DummyDB()

    def _override_get_db():
        yield dummy_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: DummyUser(1)
    app.dependency_overrides[require_at_least_viewer] = lambda: DummyAccessLevel(
        "viewer"
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_get_location_summary_returns_payload(client, monkeypatch):
    """
    Patch get_cached_location_summary at the router level to simulate a cache
    hit and avoid touching the real database/ORM.
    """
    from app.dcim.routers import summary_router

    sample_payload = {
        "total_locations": 1,
        "results": [{"id": 1, "name": "Loc1", "total_devices": 5, "total_racks": 2, "total_device_types": 3}],
    }

    monkeypatch.setattr(
        summary_router, "get_cached_location_summary", lambda: sample_payload
    )

    response = client.get("/api/dcim/summary/locations")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == sample_payload


