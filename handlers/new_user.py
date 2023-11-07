import os
import asyncio
import logging
import config
import messages
import keyboards
import file_ids
import pymongo
import utils

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage

from aiogram import Bot, Dispatcher, F, types
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

import handlers.generate_look as generate_look
import handlers.user_in_menu as user_in_menu


mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client[config.db_name]
# mongo_users = mongo_db['users']
mongo_fittings = mongo_db['fittings']


router = Router()
# user_file_id = {} #класть в бд


class AddNewUser(StatesGroup):
    choosing_sex = State()
    uploading_photo = State()
    confirming_photo = State()
    done_fill_parameters = State()
    # in_menu = State()


# выводит кнопки
@router.message(Command("start"))
async def gender_selection(message: types.Message, state: FSMContext):
    dict = {'user_id': message.from_user.id, 'fittings_amount': 15}
    print('id', message.from_user.id)
    mongo_fittings.insert_one(dict)

    await message.answer_animation(animation=file_ids.file_ids['choose_sex'], 
                                    caption=messages.gender_selection, 
                                    reply_markup=keyboards.get_gender_selection_kb())
    await state.clear()
    await state.update_data({'count': 15})
    await state.set_state(AddNewUser.choosing_sex)

    await utils.send_event_to_amplitude(message.chat.id, state, 'first_launch')


@router.message(Command("add_fittings"))
async def add_fittings(message: types.Message, command: CommandObject):
    if not message.chat.id in config.ids_to_send:
        await message.answer('Нет прав на это действие')
        return
    if command.args:
        params = command.args.split(' ')
        user_in_db = mongo_fittings.find_one({'user_id': int(params[0])})
        print(user_in_db)
        fittings_count = user_in_db['fittings_amount']
        mongo_fittings.update_one({'user_id': int(params[0])}, {'$set': {"fittings_amount" : fittings_count + int(params[1])}})
        print(user_in_db)
        await message.answer('Лимит добавлен')
    else:
        await message.answer("Введите команду в виде 'user_id num_add_fittings'")


@router.message(Command("set_fittings"))
async def set_fittings(message: types.Message, command: CommandObject):
    if not message.chat.id in config.ids_to_send:
        await message.answer('Нет прав на это действие')
        return
    if command.args:
        params = command.args.split(' ')
        mongo_fittings.update_one({'user_id': int(params[0])}, {'$set': {"fittings_amount" : int(params[1])}})
        await message.answer('Лимит добавлен')
    else:
        await message.answer("Введите команду в виде 'user_id num_set_fittings'")


@router.message(AddNewUser.uploading_photo, F.text=='⬅️ Назад')
async def upload_photo(message: types.Message, state: FSMContext):
    await gender_selection(message, state)  


# @router.message(Command("remove"))
# async def gender_selection(message: types.Message, state: FSMContext):
#     # mongo_users.delete_one({'chat_id': message.chat.id})
#     await message.answer('Удален')


async def upload_photo_message(message):
    await message.answer_animation(animation=file_ids.file_ids['photo_upload'], 
                                    caption=messages.uploading_photos,
                                    reply_markup=keyboards.get_back_uploading_photo())


# ловит один из вариантов выбора полов и выводит сообщение о загрузке фото
sex_names = ['♂ Мужской', '♀ Женский']
@router.message(AddNewUser.choosing_sex, F.text.in_(sex_names))
async def choosing_sex(message: types.Message,  state: FSMContext):
    try:
        if message.text == sex_names[0]:
            await state.update_data(sex='man')
        else:
            await state.update_data(sex='woman')

        await upload_photo_message(message)
        
        await state.set_state(AddNewUser.uploading_photo)
    except Exception as e:
        await gender_selection(message, state)  


@router.message(AddNewUser.choosing_sex)
async def sex_chosen_incorrectly(message: Message):
    await message.answer(
        text=messages.gender_selection,
        reply_markup=keyboards.get_gender_selection_kb()
    )


# Загрузка пользователем его фото
@router.message(AddNewUser.uploading_photo, F.photo)
async def upload_photo(message: types.Message, bot: Bot, state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        file_name = f"tmps/{user_id}.jpg"
        await state.update_data({'file_name': file_name})
        utils.remove(file_name)

        await bot.download(
            message.photo[-1],
            destination=file_name
        )

        await message.answer_photo(
            FSInputFile(file_name),
            caption=messages.confirm_photo,
            reply_markup=keyboards.confirm_photo()
        )

        await state.set_state(AddNewUser.confirming_photo)
    except Exception as e:
        await gender_selection(message, state)  


@router.message(AddNewUser.uploading_photo)
async def photo_uploaded_incorrectly(message: Message, bot: Bot):
    await message.answer(
        text=messages.uploading_photos,
        reply_markup=ReplyKeyboardRemove()
    )


# Изменить загруженное фото
@router.message(AddNewUser.confirming_photo, F.text=='🔄 Изменить')
async def change_photo(message: types.Message, state: FSMContext):
    await upload_photo_message(message)

    await state.set_state(AddNewUser.uploading_photo)


# Принять фото и идти дальше
@router.message(AddNewUser.confirming_photo, F.text=='✅ Оставить')
async def accept_photo(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        if not 'file_name' in user_data:
            await upload_photo_message(message)
            await state.set_state(AddNewUser.uploading_photo)
            return

        await message.answer_animation(
            animation=file_ids.file_ids['fitting'],
            caption=messages.choosing_way_of_generating,
            reply_markup=keyboards.accept_photo()
        )

        await state.set_state(generate_look.GenerateLook.choosing_way_of_generating)
        #await state.clear()
    except Exception as e:
        await gender_selection(message, state)  


@router.message(AddNewUser.confirming_photo)
async def photo_confirmed_incorrectly(message: Message):
    await message.answer(
        text=messages.confirm_photo,
        reply_markup=keyboards.confirm_photo()
    )