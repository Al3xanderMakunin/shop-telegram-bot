from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from html import escape

from aiogram import Bot
from sqlalchemy import select

from bot.database import Database
from bot.database.methods.audit import log_audit
from bot.database.methods.settings import get_topup_notification_settings
from bot.database.models import Payments, User
from bot.logger_mesh import logger


_CURRENCY_SYMBOLS = {
    "RUB": "₽",
    "USD": "$",
    "EUR": "€",
    "XTR": "⭐",
}


def _money(value: Decimal, currency: str) -> str:
    amount = Decimal(value).quantize(Decimal("0.01"))
    rendered = f"{amount:,.2f}".replace(",", " ")
    if rendered.endswith(".00"):
        rendered = rendered[:-3]
    symbol = _CURRENCY_SYMBOLS.get(currency.upper(), currency.upper())
    return f"{rendered} {symbol}"


def _local_datetime(value: datetime) -> str:
    # PostgreSQL returns aware values; SQLite test/dev databases may return naive
    # UTC values. Display in the host's configured local timezone.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%d.%m.%Y %H:%M:%S")


async def _notify_balance_topup(
        bot: Bot,
        *,
        user_id: int,
        user_name: str,
        provider: str,
        external_id: str,
) -> bool:
    chat_id, thread_id = await get_topup_notification_settings()
    if chat_id is None:
        return False

    async with Database().session() as session:
        row = (await session.execute(
            select(Payments, User.balance, User.referral_id)
            .outerjoin(User, User.telegram_id == Payments.user_id)
            .where(
                Payments.provider == provider,
                Payments.external_id == external_id,
                Payments.status == "succeeded",
            )
        )).one_or_none()

    if row is None:
        logger.warning(
            "Top-up notification data not found for %s:%s",
            provider, external_id,
        )
        return False

    payment, new_balance, referral_id = row
    new_balance = Decimal(new_balance or payment.amount)
    old_balance = new_balance - payment.amount
    currency = payment.currency
    completed_at = payment.updated_at or datetime.now(timezone.utc)
    event_time = datetime.now(timezone.utc)

    referrer = f"ID {referral_id}" if referral_id is not None else "нет"
    text = (
        "💰 <b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n"
        f"👤 {escape(user_name or str(user_id))} (<code>{user_id}</code>)\n"
        "💳 🔄 Пополнение\n"
        f"💵 <b>{_money(payment.amount, currency)}</b>\n"
        f"📉 {_money(old_balance, currency)} → "
        f"📈 {_money(new_balance, currency)} "
        f"(<b>+{_money(payment.amount, currency)}</b>)\n"
        f"🔗 Реферер: {referrer}\n"
        f"<blockquote>ID транзакции: {payment.id}</blockquote>\n"
        f"Способ оплаты: <code>{escape(payment.provider)}</code>\n"
        f"Внешний ID: <code>{escape(payment.external_id)}</code>\n\n"
        f"Создана: {_local_datetime(payment.created_at)}\n"
        f"Завершена: {_local_datetime(completed_at)}\n"
        f"<i>{_local_datetime(event_time)}</i>"
    )

    kwargs = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if thread_id is not None:
        kwargs["message_thread_id"] = thread_id

    try:
        await bot.send_message(**kwargs)
        return True
    except Exception as exc:
        logger.warning(
            "Failed to send top-up notification to chat %s, thread %s: %s",
            chat_id, thread_id, exc,
        )
        await log_audit(
            "topup_notification_failed",
            level="WARNING",
            user_id=user_id,
            resource_type="Payment",
            resource_id=str(payment.id),
            details=f"chat_id={chat_id}, thread_id={thread_id}, error={exc}",
        )
        return False


async def notify_balance_topup(
        bot: Bot,
        *,
        user_id: int,
        user_name: str,
        provider: str,
        external_id: str,
) -> bool:
    """Best-effort top-up alert; failures never break the payment flow."""
    try:
        return await _notify_balance_topup(
            bot,
            user_id=user_id,
            user_name=user_name,
            provider=provider,
            external_id=external_id,
        )
    except Exception as exc:
        logger.warning(
            "Unexpected top-up notification failure for %s:%s: %s",
            provider, external_id, exc,
        )
        try:
            await log_audit(
                "topup_notification_failed",
                level="WARNING",
                user_id=user_id,
                resource_type="Payment",
                resource_id=external_id[:128],
                details=f"provider={provider}, error={exc}",
            )
        except Exception:
            logger.exception("Could not write top-up notification failure to audit log")
        return False
