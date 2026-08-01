from sqlalchemy import select, update

from bot.database import Database
from bot.database.models import BotSettings


async def get_paypear_settings() -> dict:
    """Return PayPear credentials and checkout settings from the admin-managed row."""
    async with Database().session() as s:
        row = (await s.execute(
            select(
                BotSettings.paypear_enabled,
                BotSettings.paypear_shop_id,
                BotSettings.paypear_secret_key,
                BotSettings.paypear_payment_method,
                BotSettings.paypear_return_url,
            ).where(BotSettings.id == 1)
        )).one_or_none()
        if row is None:
            return {
                "enabled": False, "shop_id": None, "secret_key": None,
                "payment_method": "sbp", "return_url": None,
            }
        return {
            "enabled": bool(row.paypear_enabled),
            "shop_id": row.paypear_shop_id,
            "secret_key": row.paypear_secret_key,
            "payment_method": row.paypear_payment_method or "sbp",
            "return_url": row.paypear_return_url,
        }


async def is_paypear_configured() -> bool:
    settings = await get_paypear_settings()
    return bool(
        settings["enabled"]
        and settings["shop_id"]
        and settings["secret_key"]
        and settings["return_url"]
    )

async def get_platega_settings() -> dict:
    async with Database().session() as s:
        row = (await s.execute(select(BotSettings.platega_enabled, BotSettings.platega_merchant, BotSettings.platega_secret, BotSettings.platega_return_url).where(BotSettings.id == 1))).one_or_none()
        if not row: return {"enabled": False, "merchant": None, "secret": None, "return_url": None}
        return {"enabled": bool(row.platega_enabled), "merchant": row.platega_merchant, "secret": row.platega_secret, "return_url": row.platega_return_url}

async def is_platega_configured() -> bool:
    x = await get_platega_settings(); return bool(x["enabled"] and x["merchant"] and x["secret"] and x["return_url"])


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
