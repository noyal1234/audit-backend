"""Dealer contact: create with contact, validation 422, GET/PATCH contact, Employee 403."""

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.api.dependencies import get_current_user_payload
from src.business_services.auth_service import ROLE_EMPLOYEE, ROLE_SUPER_ADMIN


def _super_admin_payload() -> dict:
    return {
        "sub": "test-super-admin-id",
        "email": "super@test.com",
        "role_type": ROLE_SUPER_ADMIN,
        "facility_id": None,
        "zone_id": None,
    }


def _employee_payload(facility_id: str) -> dict:
    return {
        "sub": "test-employee-id",
        "email": "emp@test.com",
        "role_type": ROLE_EMPLOYEE,
        "facility_id": facility_id,
        "zone_id": None,
    }


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def override_auth(client: TestClient):
    app.dependency_overrides[get_current_user_payload] = _super_admin_payload
    yield
    app.dependency_overrides.pop(get_current_user_payload, None)


def test_create_dealership_with_contact_success(client: TestClient) -> None:
    """Create zone, then dealership with dealer contact; assert 201 and contact stored."""
    zone_r = client.post("/zones", json={"name": "Contact Test Zone"})
    assert zone_r.status_code == 201, zone_r.text
    zone_id = zone_r.json()["id"]

    body = {
        "name": "ABC Motors",
        "zone_id": zone_id,
        "dealer_name": "John Doe",
        "dealer_phone": "+91-9876543210",
        "dealer_email": "john@abcmotors.com",
        "dealer_designation": "Owner",
    }
    r = client.post("/dealerships", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["dealer_name"] == "John Doe"
    assert data["dealer_phone"] == "+91-9876543210"
    assert data["dealer_email"] == "john@abcmotors.com"
    assert data["dealer_designation"] == "Owner"

    fac_id = data["id"]
    get_r = client.get(f"/dealerships/{fac_id}/contact")
    assert get_r.status_code == 200
    contact = get_r.json()
    assert contact["dealer_name"] == "John Doe"
    assert contact["dealer_phone"] == "+91-9876543210"
    assert contact["dealer_email"] == "john@abcmotors.com"
    assert contact["dealer_designation"] == "Owner"


def test_create_dealership_without_dealer_name_returns_422(client: TestClient) -> None:
    """Create dealership without dealer_name; assert 422."""
    zone_r = client.post("/zones", json={"name": "Validation Test Zone"})
    assert zone_r.status_code == 201, zone_r.text
    zone_id = zone_r.json()["id"]

    body = {
        "name": "No Contact Motors",
        "zone_id": zone_id,
        "dealer_phone": "+91-9876543210",
        "dealer_email": "noconact@test.com",
    }
    r = client.post("/dealerships", json=body)
    assert r.status_code == 422, r.text


def test_update_dealer_contact_persists(client: TestClient) -> None:
    """Create dealership, PATCH contact, then GET contact and assert updated."""
    zone_r = client.post("/zones", json={"name": "Update Contact Zone"})
    assert zone_r.status_code == 201, zone_r.text
    zone_id = zone_r.json()["id"]

    create_body = {
        "name": "Update Motors",
        "zone_id": zone_id,
        "dealer_name": "Jane Doe",
        "dealer_phone": "+1-555-1234567",
        "dealer_email": "jane@updatemotors.com",
    }
    cr = client.post("/dealerships", json=create_body)
    assert cr.status_code == 201, cr.text
    fac_id = cr.json()["id"]

    patch_r = client.patch(
        f"/dealerships/{fac_id}/contact",
        json={"dealer_phone": "+1-555-9998888", "dealer_designation": "Manager"},
    )
    assert patch_r.status_code == 200, patch_r.text
    updated = patch_r.json()
    assert updated["dealer_phone"] == "+1-555-9998888"
    assert updated["dealer_designation"] == "Manager"
    assert updated["dealer_name"] == "Jane Doe"

    get_r = client.get(f"/dealerships/{fac_id}/contact")
    assert get_r.status_code == 200
    contact = get_r.json()
    assert contact["dealer_phone"] == "+1-555-9998888"
    assert contact["dealer_designation"] == "Manager"


def test_employee_get_contact_returns_403(client: TestClient) -> None:
    """Employee role cannot call GET /dealerships/{id}/contact."""
    app.dependency_overrides[get_current_user_payload] = lambda: _employee_payload("any-facility-id")
    try:
        r = client.get("/dealerships/any-uuid/contact")
        assert r.status_code == 403, r.text
    finally:
        app.dependency_overrides[get_current_user_payload] = _super_admin_payload


def test_employee_patch_contact_returns_403(client: TestClient) -> None:
    """Employee role cannot call PATCH /dealerships/{id}/contact."""
    app.dependency_overrides[get_current_user_payload] = lambda: _employee_payload("any-facility-id")
    try:
        r = client.patch(
            "/dealerships/any-uuid/contact",
            json={"dealer_phone": "+1-555-0000000"},
        )
        assert r.status_code == 403, r.text
    finally:
        app.dependency_overrides[get_current_user_payload] = _super_admin_payload
