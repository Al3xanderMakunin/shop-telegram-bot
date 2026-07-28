from decimal import Decimal

import pytest

from bot.database.methods.settings import set_topup_notification_settings
from bot.database.methods.transactions import process_payment_with_referral
from bot.misc.services.topup_notifier import notify_balance_topup


@pytest.mark.asyncio
async def test_topup_notification_is_sent_to_configured_thread(
        user_factory,
        mock_bot,
):
    await user_factory(telegram_id=350, balance=0)
    await user_factory(telegram_id=1007604696, balance=0, referral_id=350)
    await set_topup_notification_settings(-1001234567890, 77)

    success, message = await process_payment_with_referral(
        user_id=1007604696,
        amount=Decimal("315"),
        provider="paypear",
        external_id="e74fe9ee-53ba-47a8-81cc-5b88dbdf7315",
    )
    assert (success, message) == (True, "success")

    sent = await notify_balance_topup(
        mock_bot,
        user_id=1007604696,
        user_name="Ксения",
        provider="paypear",
        external_id="e74fe9ee-53ba-47a8-81cc-5b88dbdf7315",
    )

    assert sent is True
    kwargs = mock_bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == -1001234567890
    assert kwargs["message_thread_id"] == 77
    assert kwargs["parse_mode"] == "HTML"
    assert "Ксения" in kwargs["text"]
    assert "315 ₽" in kwargs["text"]
    assert "0 ₽" in kwargs["text"]
    assert "Реферер: ID 350" in kwargs["text"]
    assert "<blockquote>ID транзакции:" in kwargs["text"]
    assert "Способ оплаты: <code>paypear</code>" in kwargs["text"]


@pytest.mark.asyncio
async def test_topup_notification_is_skipped_when_destination_is_disabled(mock_bot):
    sent = await notify_balance_topup(
        mock_bot,
        user_id=1,
        user_name="User",
        provider="test",
        external_id="missing",
    )

    assert sent is False
    mock_bot.send_message.assert_not_awaited()
