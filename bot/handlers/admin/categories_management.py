from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from bot.i18n import localize, esc
from bot.handlers.other import caller_name
from bot.database.models import Permission
from bot.database.methods import (check_category_cached, create_category, delete_category,
                                  update_category, get_all_category_names)
from bot.keyboards.inline import back, simple_buttons, choice_buttons
from bot.filters import HasPermissionFilter
from bot.database.methods.audit import log_audit
from bot.misc import CategoryRequest
from bot.states import CategoryFSM

router = Router()


@router.callback_query(F.data == 'categories_management', HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def categories_callback_handler(call: CallbackQuery):
    """
    Opens the categories management submenu.
    """
    actions = [
        (localize("admin.categories.add"), "add_category"),
        (localize("admin.categories.rename"), "update_category"),
        (localize("admin.categories.delete"), "delete_category"),
        ("🖼 Медиа категории", "category_media"),
        (localize("btn.back"), "console"),
    ]
    await call.message.edit_text(
        localize("admin.categories.menu.title"),
        reply_markup=simple_buttons(actions, per_row=1),
    )


@router.callback_query(F.data == 'add_category', HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def add_category_callback_handler(call: CallbackQuery, state):
    """
    Asks admin for a new category name.
    """
    await call.message.edit_text(
        localize("admin.categories.prompt.add"),
        reply_markup=back("categories_management"),
    )
    await state.set_state(CategoryFSM.waiting_add_category)


@router.message(CategoryFSM.waiting_add_category, F.text)
async def process_category_for_add(message: Message, state):
    """Creates a category if it doesn't exist yet."""
    try:
        # Validate category name
        category_request = CategoryRequest(name=message.text.strip())
        category_name = category_request.sanitize_name()

        if await check_category_cached(category_name):
            await message.answer(
                localize("admin.categories.add.exist"),
                reply_markup=back("categories_management"),
            )
        else:
            await create_category(category_name)
            await message.answer(
                localize("admin.categories.add.success"),
                reply_markup=back("categories_management"),
            )

            admin_name = caller_name(message)
            await log_audit("create_category", user_id=message.from_user.id, resource_type="Category",
                            resource_id=category_name, details=f"admin={admin_name}")

    except Exception as e:
        await message.answer(
            localize("errors.invalid_data"),
            reply_markup=back("categories_management"),
        )
        await log_audit("create_category_error", level="ERROR", user_id=message.from_user.id, resource_type="Category",
                        details=str(e))

    await state.clear()


@router.callback_query(F.data == 'delete_category', HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def delete_category_callback_handler(call: CallbackQuery, state):
    """
    Asks admin for a category name to delete.
    """
    categories = await get_all_category_names()
    if not categories:
        await call.message.edit_text(localize("admin.categories.delete.not_found"),
                                     reply_markup=back("categories_management"))
        await state.set_state(CategoryFSM.waiting_delete_category)
        return
    await state.update_data(category_options=categories)
    await call.message.edit_text(localize("admin.categories.prompt.delete"),
                                 reply_markup=choice_buttons(categories, "cat_delete:", "categories_management"))
    await state.set_state(CategoryFSM.waiting_delete_category)


@router.callback_query(F.data.startswith("cat_delete:"), CategoryFSM.waiting_delete_category,
                       HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def delete_category_by_button(call: CallbackQuery, state):
    data = await state.get_data()
    try:
        category_name = data["category_options"][int(call.data.split(":")[1])]
    except (KeyError, ValueError, IndexError, TypeError):
        await call.answer(localize("errors.invalid_data"), show_alert=True)
        return
    await delete_category(category_name)
    await call.message.edit_text(localize("admin.categories.delete.success"),
                                 reply_markup=back("categories_management"))
    await log_audit("delete_category", user_id=call.from_user.id, resource_type="Category",
                    resource_id=category_name, details=f"admin={caller_name(call)}")
    await state.clear()


# --- Handle category deletion
@router.message(CategoryFSM.waiting_delete_category, F.text)
async def process_category_for_delete(message: Message, state):
    """
    Deletes a category by name if it exists.
    """
    category_name = message.text.strip()

    if not await check_category_cached(category_name):
        await message.answer(
            localize("admin.categories.delete.not_found"),
            reply_markup=back("categories_management"),
        )
    else:
        await delete_category(category_name)
        await message.answer(
            localize("admin.categories.delete.success"),
            reply_markup=back("categories_management"),
        )
        admin_name = caller_name(message)
        await log_audit("delete_category", user_id=message.from_user.id, resource_type="Category",
                        resource_id=category_name, details=f"admin={admin_name}")

    await state.clear()


@router.callback_query(F.data == 'update_category', HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def update_category_callback_handler(call: CallbackQuery, state):
    """
    Asks admin for current category name before renaming.
    """
    categories = await get_all_category_names()
    if not categories:
        await call.message.edit_text(localize("admin.categories.rename.not_found"),
                                     reply_markup=back("categories_management"))
        await state.set_state(CategoryFSM.waiting_update_category)
        return
    await state.update_data(category_options=categories)
    await call.message.edit_text(localize("admin.categories.prompt.rename.old"),
                                 reply_markup=choice_buttons(categories, "cat_rename:", "categories_management"))
    await state.set_state(CategoryFSM.waiting_update_category)


@router.callback_query(F.data.startswith("cat_rename:"), CategoryFSM.waiting_update_category,
                       HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def select_category_for_update(call: CallbackQuery, state):
    data = await state.get_data()
    try:
        old_name = data["category_options"][int(call.data.split(":")[1])]
    except (KeyError, ValueError, IndexError, TypeError):
        await call.answer(localize("errors.invalid_data"), show_alert=True)
        return
    await state.update_data(old_category=old_name)
    await call.message.edit_text(localize("admin.categories.prompt.rename.new"),
                                 reply_markup=back("categories_management"))
    await state.set_state(CategoryFSM.waiting_update_category_name)


@router.message(CategoryFSM.waiting_update_category, F.text)
async def check_category_for_update(message: Message, state):
    """
    Verifies the category exists, then prompts for a new name.
    """
    old_name = message.text.strip()

    if not await check_category_cached(old_name):
        await message.answer(
            localize("admin.categories.rename.not_found"),
            reply_markup=back("categories_management"),
        )
        await state.clear()
        return

    await state.update_data(old_category=old_name)
    await message.answer(
        localize("admin.categories.prompt.rename.new"),
        reply_markup=back("categories_management"),
    )
    await state.set_state(CategoryFSM.waiting_update_category_name)


@router.message(CategoryFSM.waiting_update_category_name, F.text)
async def check_category_name_for_update(message: Message, state):
    """
    Renames a category to the new name.
    """
    new_name = message.text.strip()
    data = await state.get_data()
    old_name = data.get("old_category")

    if await check_category_cached(new_name):
        await message.answer(
            localize("admin.categories.rename.exist"),
            reply_markup=back("categories_management"),
        )
        await state.clear()
        return

    await update_category(old_name, new_name)
    await message.answer(
        localize("admin.categories.rename.success", old=esc(old_name), new=esc(new_name)),
        reply_markup=back("categories_management"),
    )

    admin_name = caller_name(message)
    await log_audit("rename_category", user_id=message.from_user.id, resource_type="Category", resource_id=new_name,
                    details=f"admin={admin_name}, old_name={old_name}")

    await state.clear()
