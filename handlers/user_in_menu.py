import asyncio
import logging
import config
import messages
import keyboards
import pymongo
import main
import utils

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage

from aiogram import Bot, Dispatcher, F, types
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import handlers.generate_look as generate_look
import handlers.new_user as new_user
import handlers.save_look as save_look

import file_ids

router = Router()
bot =  main.bt
#src = new_user.src
# pro = 'false'

# mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
# mongo_db = mongo_client[config.db_name]
# mongo_users = mongo_db['users']

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client[config.db_name]
mongo_fittings = mongo_db['fittings']


class InMenu(StatesGroup):
    in_menu = State()
    start_generation = State()
    changing_sex = State()
    changing_photo = State()
    confirming_photo = State()
    go_to_pro = State()


@router.message(InMenu.in_menu, F.text=='✨ Создать образ')
async def tap_generate_look_but(message: types.Message, state: FSMContext):
    try:
        user_id = message.chat.id

        user_in_db = mongo_fittings.find_one({'user_id': user_id})
        print('id', message.chat.id)
        fittings_count = user_in_db['fittings_amount']

        if fittings_count <= 0:
            await tap_PRO_but(message, state)
            return
        
        await new_user.accept_photo(message, state)

        await utils.send_event_to_amplitude(message.chat.id, state, 'menu_create_press')
    except Exception as e:
        print(e)
        await save_look.finish(message, state)


@router.message(InMenu.in_menu, F.text=='Изменить пол')
async def tap_change_sex_but(message: types.Message,  state: FSMContext):
    try:
        await message.answer(messages.gender_selection, reply_markup=keyboards.get_gender_selection_kb())
        await state.set_state(InMenu.changing_sex)
    except Exception as e:
        print(e)
        await save_look.finish(message, state)


# ловит один из вариантов выбора полов и выводит клавиатуру меню
sex_names = ['♂ Мужской', '♀ Женский']
@router.message(InMenu.changing_sex, F.text.in_(sex_names))
async def changing_sex(message: types.Message,  state: FSMContext):
    try:
        if message.text == sex_names[0]:
            await state.update_data(sex='man')
        else:
            await state.update_data(sex='woman')

        # await new_user.upload_photo_message(message)
        user_data = await state.get_data()
        file_name = user_data['file_name']
        await message.answer_photo(
            FSInputFile(file_name),
            caption=messages.confirm_photo,
            reply_markup=keyboards.confirm_photo()
        )

        await state.set_state(InMenu.confirming_photo)
        
        # await save_look.finish(message, state)
    except Exception as e:
        print(e)
        await save_look.finish(message, state)


@router.message(InMenu.changing_sex)
async def sex_changing_incorrectly(message: Message):
    await new_user.sex_chosen_incorrectly(message)


@router.message(InMenu.in_menu, F.text=='Изменить ваше фото')
async def tap_change_photo_but(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        file_name = user_data['file_name']
        await message.answer_photo(
            FSInputFile(file_name),
            caption=messages.confirm_photo,
            reply_markup=keyboards.confirm_photo()
        )
        
        await state.set_state(InMenu.confirming_photo)
    except Exception as e:
        print(e)
        await save_look.finish(message, state)
    

@router.message(InMenu.changing_photo, F.photo)
async def changing_photo(message: types.Message, bot: Bot,  state: FSMContext):
    try:
        user_id = str(message.from_user.id)
        file_name = f"tmps/{user_id}.jpg"

        await state.update_data({'file_name': file_name})

        await bot.download(
            message.photo[-1],
            destination=file_name
        )

        # await asyncio.sleep(2)

        await message.answer_photo(
            FSInputFile(file_name),
            caption=messages.confirm_photo,
            reply_markup=keyboards.confirm_photo()
        )

        await state.set_state(InMenu.confirming_photo) # !!!!!!!
    except Exception as e:
        print(e)
        await save_look.finish(message, state)
    

@router.message(InMenu.changing_photo, F.text=='⬅️ Назад')
async def changing_photo(message: types.Message, bot: Bot,  state: FSMContext):
    await save_look.finish(message, state)


@router.message(InMenu.changing_photo)
async def photo_changed_incorrectly(message: Message, bot: Bot):
    await message.answer(
        text= "Пожалуйста, загрузите ваше фото",
        reply_markup=keyboards.types.ReplyKeyboardRemove()
    )


# Изменить загруженное фото
@router.message(InMenu.confirming_photo, F.text=='🔄 Изменить')
async def change_photo(message: types.Message, state: FSMContext):
    try:
        await new_user.upload_photo_message(message)

        await state.set_state(InMenu.changing_photo)
    except Exception as e:
        print(e)
        await save_look.finish(message, state)


# Принять фото и вернуться в меню
@router.message(InMenu.confirming_photo, F.text=='✅ Оставить')
async def accept_photo(message: types.Message, state: FSMContext):
    await save_look.finish(message, state)

    await state.set_state(InMenu.in_menu)


@router.message(InMenu.confirming_photo)
async def photo_confirmed_incorrectly(message: Message):
    await message.answer(
        text= "Пожалуйста, подтвердите загрузку фото",
        reply_markup=keyboards.confirm_photo()
    )


@router.message(InMenu.in_menu, F.text=='💯 Пополнить примерки')
async def tap_PRO_but(message: types.Message, state: FSMContext):
    try:
        username = ''
        try:
            username = message.from_user.username
        except Exception as e:
            print('Юзернейма нет')

        for id in config.ids_to_send:
            await bot.send_message(id, f"/add_fittings {message.from_user.id} {username}")

        await message.answer_animation(
            animation=file_ids.file_ids['pro_content'],
            caption=messages.go_to_pro,
            reply_markup=keyboards.go_to_pro()
        )

        if message.text == '💯 Пополнить примерки':
            await utils.send_event_to_amplitude(message.chat.id, state, 'menu_pay_press')
        await utils.send_event_to_amplitude(message.chat.id, state, 'pay_preview_open')
    except Exception as e:
        print(e)
        await save_look.finish(message, state)


@router.message(InMenu.in_menu)
async def menu_incorrectly(message: Message):
    await message.answer(
        text= "Пожалуйста, выберите следующее действие",
        reply_markup=keyboards.get_welcome_screen()
    )
