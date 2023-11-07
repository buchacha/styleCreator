from aiogram.filters.callback_data import CallbackData

class ParamsCallbackFactory(CallbackData, prefix="choice"):
    index: int
    data: str
    state: str