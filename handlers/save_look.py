import asyncio
import logging
import config
import keyboards
import pymongo
import utils

# from aiogram import html
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher, F, types
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile, URLInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import handlers.user_in_menu as user_in_menu
import handlers.generate_look as generate_look
import handlers.new_user as new_user
import main
import file_ids
import messages

#bot = main.bt
router = Router()
pro = 'false'

work_folder = 'Self-Correction-Human-Parsing'

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client[config.db_name]
# mongo_users = mongo_db['users']
mongo_fittings = mongo_db['fittings']


class SaveLook(StatesGroup):
    choosing_generated_look = State()
    looking_in_shop = State()
    saving_look = State()



@router.callback_query(SaveLook.choosing_generated_look, F.data.startswith("nok"))
async def choosing_generated_look_cb(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except Exception as e:
        print(e)
        await finish(callback.message, state)


@router.message(SaveLook.choosing_generated_look, F.text=='🏠 В меню')
async def tap_to_menu(message: types.Message, state: FSMContext):
    await message.answer(messages.expect)


@router.callback_query(SaveLook.choosing_generated_look, F.data.startswith("ok"))
async def choosing_generated_look_cb(callback: types.CallbackQuery, state: FSMContext):
    try:
        await generate_look.send_expectation_messages_first(callback.message)
        await utils.send_event_to_amplitude(callback.message.chat.id, state, 'looks_look_choose')

        # обращение к апи
        user_data = await state.get_data()
        print(user_data)
        image_path = user_data['output'][int(callback.data.split('_')[-1])]
        print(image_path)
        await state.update_data({'look_path': image_path})
        # img_url = utils.upload_image(image_path)

        result = await utils.get_info_from_api(f'{work_folder}/search/{image_path}')
        print(result)

        await generate_look.send_expectation_messages_second(callback.message, messages.find_clothes)
        await generate_look.send_expectation_messages_third(callback.message, messages.find_clothes)

        for item in result:
            await callback.message.answer_photo(
                URLInputFile(item['url_img']),
                caption=item['text'],
                reply_markup=keyboards.save_look(item['url_shop'])
            )

        await callback.message.answer(messages.finded_clothes, reply_markup=keyboards.next())

        await state.set_state(SaveLook.looking_in_shop)

        await utils.send_event_to_amplitude(callback.message.chat.id, state, 'clothes_search_finish')
    except Exception as e:
        print(e)
        await finish(callback.message, state)


@router.message(SaveLook.looking_in_shop, F.text=='Завершить 🎉')
async def saving_look(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()

        image_path = user_data['look_path']
        img_url = await utils.upload_image(f'{work_folder}/output_generation/{image_path}')
        await message.answer_photo(
            URLInputFile(img_url),
            caption=messages.save_image + '\n\n' + '[Участвовать прямо сейчас](https://t.me/stylecreatorchat)', 
            reply_markup=keyboards.finish(),
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # await message.answer_animation(
        #     animation=file_ids.file_ids['share'],
        #     caption=messages.save_image,
        #     reply_markup=keyboards.finish()
        # )
        await state.set_state(SaveLook.saving_look)

        await utils.send_event_to_amplitude(message.chat.id, state, 'final_finish_press')
    except Exception as e:
        print(e)
        await finish(message, state)


@router.message(SaveLook.looking_in_shop)
async def saving_look_incorrectly(message: types.Message, state: FSMContext):
    try:
        await message.answer_photo(
            caption=messages.saving_look,
            reply_markup=keyboards.save_look()
        )
    except Exception as e:
        print(e)
        await finish(message, state)
     

@router.message(SaveLook.saving_look, F.text=='🔄 Еще образ')
async def another_image(message: types.Message, state: FSMContext):
    try:
        user_id = message.chat.id

        user_in_db = mongo_fittings.find_one({'user_id': user_id})
        print('id', message.chat.id)
        fittings_count = user_in_db['fittings_amount']

        if fittings_count <= 0:
            await user_in_menu.tap_PRO_but(message, state)
            return
        
        await new_user.accept_photo(message,  state)

    except Exception as e:
        print(e)
        await finish(message, state)

    
@router.message(SaveLook.saving_look, F.text=='🏠 В меню')
async def finish(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        user_id = message.chat.id

        gif = 'hello_' + (user_data['sex'] if 'sex' in user_data else 'man')

        await message.answer_animation(
            animation=file_ids.file_ids[gif],
            caption=messages.in_menu,
            reply_markup=keyboards.get_welcome_screen(pro)
        )

        #fittings_count = user_data['count']
        user_in_db = mongo_fittings.find_one({'user_id': user_id})
        fittings_count = user_in_db['fittings_amount']
        await message.answer('Осталось примерок: ' + str(fittings_count))

        await state.set_state(user_in_menu.InMenu.in_menu)
    except Exception as e:
        print(e)
        await message.answer('Осталось примерок: ', reply_markup=keyboards.get_welcome_screen(pro))
        await state.set_state(user_in_menu.InMenu.in_menu)



@router.message(SaveLook.saving_look) # not F.text.in_
async def finish_incorrectly(message: types.Message):
    await message.answer( 
        text=messages.saving_look_finish,
        reply_markup=keyboards.finish()
    )
