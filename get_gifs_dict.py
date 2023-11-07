import asyncio
import logging
import config
import messages
import redis
import keyboards

import pymongo
from pymongo import MongoClient

# from aiogram import Bot, Dispatcher, executor, types
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums.dice_emoji import DiceEmoji
from aiogram.filters.command import Command

from typing import Optional
from aiogram.filters.callback_data import CallbackData

from aiogram.types import FSInputFile, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder


from aiogram.fsm.storage.redis import RedisStorage


import config
import keyboards
from callback_classes import *

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

OK = '✅ '
NOK = '❌ '

logging.basicConfig(level=logging.INFO)

storage = RedisStorage.from_url('redis://localhost:6379/0')  # не уверен

bot = Bot(token=config.token)
dp = Dispatcher(storage=storage)


src = []
user_data = {'user_id': None,
             'sex': None,
             'photo': None,
             'fittings_amount': 15,
             'pro': 'false'}
now_user_db = {}
gif_dict = {}

# Хэндлер на команду /start
@dp.message(Command("start"))
async def gender_selection(message: types.Message):
    global now_user_db, user_data

    user_data['user_id'] = message.from_user.id

    #if mongo_users.find_one({'user_id': message.from_user.id}) is None:
        # экран для новенького
    await message.answer(messages.gender_selection, reply_markup=keyboards.get_gender_selection())


    global gif_dict
    gif_dict = {}


# Для словаря анимаций
@dp.message(F.document)
async def handle_gif(message: types.Message):
    print(message)

    animation = message.animation
    file_unique_id = animation.file_id
    file_name = animation.file_name.split(".")[0]
    
    gif_dict[file_name] = file_unique_id

    await message.answer(str(gif_dict))


async def main():
    # dp.message.register(cmd_start, Command("test2"))

    # Запускаем бота и пропускаем все накопленные входящие
    # Да, этот метод можно вызвать даже если у вас поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())