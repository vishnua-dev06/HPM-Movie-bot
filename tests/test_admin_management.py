"""Unit and integration tests for multiple administrator management."""

import pytest
from config import settings
from database.admins import AdminRepository


@pytest.mark.asyncio
async def test_admin_bootstrap_and_owner_assignment():
    """Verify initial bootstrap creates owner and admin records from environment configuration."""
    env_admins = [1110001, 1110002]
    await AdminRepository.bootstrap_admins(env_admins)

    assert await AdminRepository.is_admin(1110001) is True
    assert await AdminRepository.is_admin(1110002) is True
    assert await AdminRepository.is_owner(1110001) is True
    assert await AdminRepository.is_owner(1110002) is False


@pytest.mark.asyncio
async def test_add_second_and_multiple_administrators():
    """Verify adding dynamic administrators through the repository."""
    await AdminRepository.bootstrap_admins([1110001])

    # Add second admin
    added_2 = await AdminRepository.add_admin(admin_id=2220002, added_by=1110001, role="admin")
    assert added_2 is True

    # Add third admin
    added_3 = await AdminRepository.add_admin(admin_id=3330003, added_by=1110001, role="admin")
    assert added_3 is True

    # Re-adding existing admin returns False
    added_dup = await AdminRepository.add_admin(admin_id=2220002, added_by=1110001)
    assert added_dup is False

    # Verify count and membership
    total = await AdminRepository.count_admins()
    assert total == 3
    assert await AdminRepository.is_admin(2220002) is True
    assert await AdminRepository.is_admin(3330003) is True


@pytest.mark.asyncio
async def test_remove_administrator_and_security_guardrails():
    """Verify administrator removal, protecting owner and preventing last admin removal."""
    owner_id = settings.primary_admin_id  # 999999999
    secondary_id = 888888888

    await AdminRepository.bootstrap_admins([owner_id, secondary_id])
    assert await AdminRepository.count_admins() == 2

    # Attempt to remove secondary admin by owner -> allowed
    success, msg = await AdminRepository.remove_admin(admin_id=secondary_id, requested_by=owner_id)
    assert success is True
    assert await AdminRepository.is_admin(secondary_id) is False
    assert await AdminRepository.count_admins() == 1

    # Attempt to remove the last remaining admin -> rejected
    fail_last, msg_last = await AdminRepository.remove_admin(admin_id=owner_id, requested_by=owner_id)
    assert fail_last is False
    assert "last remaining administrator" in msg_last


@pytest.mark.asyncio
async def test_prevent_non_owner_from_removing_owner():
    """Verify that secondary administrators cannot revoke the primary owner account."""
    owner_id = settings.primary_admin_id
    secondary_id = 555555555

    await AdminRepository.bootstrap_admins([owner_id])
    await AdminRepository.add_admin(secondary_id, added_by=owner_id)

    # Secondary admin tries to remove the owner -> rejected
    success, msg = await AdminRepository.remove_admin(admin_id=owner_id, requested_by=secondary_id)
    assert success is False
    assert "cannot be removed" in msg
