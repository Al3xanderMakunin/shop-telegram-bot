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


async def get_topup_notification_settings() -> tuple[int | None, int | None]:
    """Return the destination chat and optional forum-topic ID for top-up alerts."""
    async with Database().session() as s:
        row = (await s.execute(
            select(
                BotSettings.topup_notification_chat_id,
                BotSettings.topup_notification_thread_id,
            ).where(BotSettings.id == 1)
        )).one_or_none()
        if row is None:
            return None, None
        return row.topup_notification_chat_id, row.topup_notification_thread_id


async def set_topup_notification_settings(
        chat_id: int | None,
        thread_id: int | None,
) -> None:
    """Persist the top-up alert destination in the singleton settings row."""
    chat_id = int(chat_id) if chat_id is not None else None
    thread_id = int(thread_id) if thread_id is not None else None
    if thread_id is not None and thread_id <= 0:
        raise ValueError("thread_id must be positive")
    if chat_id is None:
        thread_id = None

    async with Database().session() as s:
        result = await s.execute(
            update(BotSettings)
            .where(BotSettings.id == 1)
            .values(
                topup_notification_chat_id=chat_id,
                topup_notification_thread_id=thread_id,
            )
        )
        if result.rowcount == 0:
            s.add(BotSettings(
                id=1,
                maintenance_mode=False,
                topup_notification_chat_id=chat_id,
                topup_notification_thread_id=thread_id,
            ))
