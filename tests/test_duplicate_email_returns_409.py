"""Assert duplicate user email returns 409 and standardized error JSON."""

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.api.dependencies import get_current_user_payload
from src.business_services.auth_service import ROLE_SUPER_ADMIN


def _super_admin_payload() -> dict:
    return {
        "sub": "test-super-admin-id",
        "email": "super@test.com",
        "role_type": ROLE_SUPER_ADMIN,
        "facility_id": None,
        "zone_id": None,
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def override_auth(client: TestClient):
    """Override auth so admin/stellantis accepts without real JWT."""
    app.dependency_overrides[get_current_user_payload] = _super_admin_payload
    yield
    app.dependency_overrides.pop(get_current_user_payload, None)


def test_duplicate_email_returns_409_and_error_format(client: TestClient) -> None:
    """Create user with email X, create again with same email; assert 409 and error shape."""
    email = "duplicate-test@example.com"
    body = {
        "email": email,
        "password": "securepass123",
        "role_type": "STELLANTIS_ADMIN",
        "facility_id": None,
        "zone_id": None,
    }
    r1 = client.post("/admin/stellantis", json=body)
    assert r1.status_code in (201, 409), f"First create: expected 201 or 409, got {r1.status_code}"

    r2 = client.post("/admin/stellantis", json=body)
    assert r2.status_code == 409, f"Duplicate create must return 409, got {r2.status_code}"
    data = r2.json()
    assert "error" in data, "Response must contain 'error' key"
    err = data["error"]
    assert isinstance(err, dict), "'error' must be an object"
    assert err.get("code") == "CONFLICT"
    assert "message" in err and isinstance(err["message"], str)
    assert "already" in err["message"].lower() or "use" in err["message"].lower()
