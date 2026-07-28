from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.i18n import localize
from bot.keyboards import admin_console_keyboard, back, simple_buttons
from bot.database.methods import (
    check_role_cached,
    get_topup_notification_settings,
    set_topup_notification_settings,
)
from bot.filters import HasPermissionFilter
from bot.database.models import Permission
from bot.database.methods.audit import log_audit
from bot.middleware.security import get_auth_middleware
from bot.states import AdminSettingsFSM

router = Router()


async def _show_topup_notification_settings(event: CallbackQuery | Message) -> None:
    chat_id, thread_id = await get_topup_notification_settings()
    text = localize(
        "admin.notifications.title",
        chat_id=chat_id if chat_id is not None else localize("admin.notifications.disabled"),
        thread_id=thread_id if thread_id is not None else localize("admin.notifications.general"),
    )
    markup = simple_buttons([
        (localize("admin.notifications.set_chat"), "topup_notifications_set_chat"),
        (localize("admin.notifications.set_thread"), "topup_notifications_set_thread"),
        (localize("admin.notifications.disable"), "topup_notifications_disable"),
        (localize("btn.back"), "console"),
    ])
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
    else:
        await event.answer(text, reply_markup=markup)


@router.callback_query(F.data == 'console')
async def console_callback_handler(call: CallbackQuery, state: FSMContext):
    """
    Admin menu (only for admins and above).
    """
    user_id = call.from_user.id
    role = await check_role_cached(user_id)
    if Permission.has_any_admin_perm(role):
        mw = get_auth_middleware()
        maintenance = mw.maintenance_mode if mw else False
        await call.message.edit_text(
            localize("admin.menu.main"),
            reply_markup=admin_console_keyboard(maintenance_mode=maintenance, role=role),
        )
    else:
        await call.answer(localize("admin.menu.rights"))

    await state.clear()


@router.callback_query(F.data == 'toggle_maintenance', HasPermissionFilter(permission=Permission.SETTINGS_MANAGE))
async def toggle_maintenance_handler(call: CallbackQuery):
    """
    Toggle maintenance mode on/off.
    """
    mw = get_auth_middleware()
    if not mw:
        return

    new_state = not mw.maintenance_mode
    await mw.set_maintenance_mode(new_state)
    state_str = "ON" if mw.maintenance_mode else "OFF"
    await log_audit(
        "toggle_maintenance",
        user_id=call.from_user.id,
        details=f"admin={call.from_user.username}, state={state_str}",
    )

    if mw.maintenance_mode:
        await call.answer(localize("admin.maintenance.enabled"), show_alert=True)
    else:
        await call.answer(localize("admin.maintenance.disabled"), show_alert=True)

    role = await check_role_cached(call.from_user.id)
    await call.message.edit_text(
        localize("admin.menu.main"),
        reply_markup=admin_console_keyboard(maintenance_mode=mw.maintenance_mode, role=role),
    )


@router.callback_query(
    F.data == "topup_notifications",
    HasPermissionFilter(permission=Permission.SETTINGS_MANAGE),
)
async def topup_notifications_handler(call: CallbackQuery):
    await _show_topup_notification_settings(call)


@router.callback_query(
    F.data == "topup_notifications_set_chat",
    HasPermissionFilter(permission=Permission.SETTINGS_MANAGE),
)
async def topup_notifications_chat_prompt(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        localize("admin.notifications.chat_prompt"),
        reply_markup=back("topup_notifications"),
    )
    await state.set_state(AdminSettingsFSM.waiting_topup_chat_id)


@router.message(
    AdminSettingsFSM.waiting_topup_chat_id,
    F.text,
    HasPermissionFilter(permission=Permission.SETTINGS_MANAGE),
)
async def topup_notifications_save_chat(message: Message, state: FSMContext):
    raw = message.text.strip()
    try:
        chat_id = int(raw)
        if chat_id == 0:
            raise ValueError
    except ValueError:
        await message.answer(
            localize("admin.notifications.invalid_chat"),
            reply_markup=back("topup_notifications"),
        )
        return

    _, thread_id = await get_topup_notification_settings()
    await set_topup_notification_settings(chat_id, thread_id)
    await state.clear()
    await log_audit(
        "topup_notifications_chat_updated",
        user_id=message.from_user.id,
        details=f"chat_id={chat_id}",
    )
    await _show_topup_notification_settings(message)


@router.callback_query(
    F.data == "topup_notifications_set_thread",
    HasPermissionFilter(permission=Permission.SETTINGS_MANAGE),
)
async def topup_notifications_thread_prompt(call: CallbackQuery, state: FSMContext):
    chat_id, _ = await get_topup_notification_settings()
    if chat_id is None:
        await call.answer(localize("admin.notifications.chat_required"), show_alert=True)
        return
    await call.message.edit_text(
        localize("admin.notifications.thread_prompt"),
        reply_markup=back("topup_notifications"),
    )
    await state.set_state(AdminSettingsFSM.waiting_topup_thread_id)


@router.message(
    AdminSettingsFSM.waiting_topup_thread_id,
    F.text,
    HasPermissionFilter(permission=Permission.SETTINGS_MANAGE),
)
async def topup_notifications_save_thread(message: Message, state: FSMContext):
    raw = message.text.strip()
    try:
        thread_id = None if raw == "0" else int(raw)
        if thread_id is not None and thread_id <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            localize("admin.notifications.invalid_thread"),
            reply_markup=back("topup_notifications"),
        )
        return

    chat_id, _ = await get_topup_notification_settings()
    if chat_id is None:
        await state.clear()
        await message.answer(localize("admin.notifications.chat_required"))
        return
    await set_topup_notification_settings(chat_id, thread_id)
    await state.clear()
    await log_audit(
        "topup_notifications_thread_updated",
        user_id=message.from_user.id,
        details=f"chat_id={chat_id}, thread_id={thread_id}",
    )
    await _show_topup_notification_settings(message)


@router.callback_query(
    F.data == "topup_notifications_disable",
    HasPermissionFilter(permission=Permission.SETTINGS_MANAGE),
)
async def topup_notifications_disable(call: CallbackQuery):
    await set_topup_notification_settings(None, None)
    await log_audit(
        "topup_notifications_disabled",
        user_id=call.from_user.id,
    )
    await call.answer(localize("admin.notifications.disabled_ok"))
    await _show_topup_notification_settings(call)
