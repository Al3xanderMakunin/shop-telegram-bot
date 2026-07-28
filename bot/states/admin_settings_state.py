from aiogram.filters.state import State, StatesGroup


class AdminSettingsFSM(StatesGroup):
    waiting_topup_chat_id = State()
    waiting_topup_thread_id = State()
