from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.models import Permission
from bot.database.methods import add_catalog_media, get_all_category_names, get_all_item_names
from bot.filters import HasPermissionFilter
from bot.keyboards.inline import back, choice_buttons, simple_buttons
from bot.states import CategoryFSM, GoodsFSM

router = Router()


async def _start(call, state, owner_type):
    names = await (get_all_category_names() if owner_type == "category" else get_all_item_names())
    await state.update_data(media_owner_type=owner_type, media_options=names)
    await call.message.edit_text(
        "Выберите объект, к которому добавить медиа:",
        reply_markup=choice_buttons(names, f"media_owner:{owner_type}:", "console"),
    )
    await state.set_state(
        CategoryFSM.waiting_media_owner if owner_type == "category"
        else GoodsFSM.waiting_media_owner
    )


@router.callback_query(F.data == "category_media", HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def category_media(call: CallbackQuery, state: FSMContext):
    await _start(call, state, "category")


@router.callback_query(F.data == "item_media", HasPermissionFilter(permission=Permission.CATALOG_MANAGE))
async def item_media(call: CallbackQuery, state: FSMContext):
    await _start(call, state, "item")


@router.callback_query(F.data.startswith("media_owner:"), CategoryFSM.waiting_media_owner)
@router.callback_query(F.data.startswith("media_owner:"), GoodsFSM.waiting_media_owner)
async def select_owner(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        owner = data["media_options"][int(call.data.rsplit(":", 1)[1])]
    except (KeyError, ValueError, IndexError, TypeError):
        await call.answer("Некорректный объект", show_alert=True)
        return
    owner_type = data["media_owner_type"]
    await state.update_data(media_owner=owner)
    await call.message.edit_text(
        "Отправляйте изображения и видео по одному. Когда закончите, нажмите «Готово».",
        reply_markup=simple_buttons([("✅ Готово", "finish_catalog_media"), ("↩️ Назад", "console")]),
    )
    await state.set_state(
        CategoryFSM.waiting_media_files if owner_type == "category"
        else GoodsFSM.waiting_media_files
    )


@router.message(F.photo | F.video, CategoryFSM.waiting_media_files)
@router.message(F.photo | F.video, GoodsFSM.waiting_media_files)
async def receive_media(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id, media_type = (
        (message.photo[-1].file_id, "photo") if message.photo
        else (message.video.file_id, "video")
    )
    added = await add_catalog_media(data["media_owner_type"], data["media_owner"], media_type, file_id)
    await message.answer("✅ Медиа сохранено" if added else "ℹ️ Такое медиа уже добавлено")


@router.callback_query(F.data == "finish_catalog_media")
async def finish_media(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("✅ Медиа каталога обновлено", reply_markup=back("console"))
    await state.clear()
