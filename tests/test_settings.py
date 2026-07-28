import pytest

from bot.database.methods.settings import (
    get_maintenance_mode,
    set_maintenance_mode,
)
from bot.middleware.security import AuthenticationMiddleware


@pytest.mark.asyncio
async def test_maintenance_mode_is_persisted():
    assert await get_maintenance_mode() is False

    await set_maintenance_mode(True)
    assert await get_maintenance_mode() is True

    await set_maintenance_mode(False)
    assert await get_maintenance_mode() is False


@pytest.mark.asyncio
async def test_auth_middleware_restores_maintenance_mode_from_database(fake_cache):
    await set_maintenance_mode(True)
    # A stale cache must not override the durable setting.
    fake_cache.store["bot:maintenance_mode"] = False

    middleware = AuthenticationMiddleware()
    await middleware.load_blocked_users()

    assert middleware.maintenance_mode is True
    assert fake_cache.store["bot:maintenance_mode"] is True
