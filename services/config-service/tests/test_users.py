"""Tests for user endpoints."""

import pytest


@pytest.mark.asyncio
async def test_user_update_and_delete_write_audit_logs(client, auth_headers, test_db):
    """Test user state changes are recorded in the audit log."""
    update_response = await client.put(
        "/api/v1/users/me",
        json={"name": "Updated Test User"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    delete_response = await client.delete(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200

    actions = []
    async for entry in (
        test_db["audit_logs"].find({"resource_type": "user"}).sort("created_at", 1)
    ):
        actions.append(entry["action"])

    assert "user.update" in actions
    assert "user.delete" in actions
