from aiogram.types import InputMediaPhoto, InputMediaVideo

from bot.database.methods import get_catalog_media


async def send_catalog_media(bot, chat_id: int, owner_type: str, owner_name: str) -> None:
    """Send an album using Telegram file_ids. No files are downloaded or uploaded."""
    media = await get_catalog_media(owner_type, owner_name)
    if not media:
        return
    payload = [
        InputMediaPhoto(media=m["file_id"]) if m["media_type"] == "photo"
        else InputMediaVideo(media=m["file_id"])
        for m in media
    ]
    # Telegram albums are limited to 10 elements.
    for start in range(0, len(payload), 10):
        await bot.send_media_group(chat_id=chat_id, media=payload[start:start + 10])
