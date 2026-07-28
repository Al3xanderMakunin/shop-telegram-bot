from sqlalchemy import select, update

from bot.database import Database
from bot.database.models import BotSettings


async def get_maintenance_mode() -> bool:
    """Read the persisted maintenance-mode flag."""
    async with Database().session() as s:
        value = await s.scalar(
            select(BotSettings.maintenance_mode).where(BotSettings.id == 1)
        )
        return bool(value) if value is not None else False


async def set_maintenance_mode(enabled: bool) -> None:
    """Persist the maintenance-mode flag in the singleton settings row."""
    async with Database().session() as s:
        result = await s.execute(
            update(BotSettings)
            .where(BotSettings.id == 1)
            .values(maintenance_mode=bool(enabled))
        )
        if result.rowcount == 0:
            s.add(BotSettings(id=1, maintenance_mode=bool(enabled)))
