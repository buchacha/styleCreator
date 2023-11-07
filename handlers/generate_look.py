import asyncio
import logging
import config
import messages
import params_dict
import keyboards
import file_ids
import utils
import random
import shutil
import os
import pymongo

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage

from aiogram import Bot, Dispatcher, F, types
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile, CallbackQuery, URLInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

import handlers.new_user as new_user
import handlers.user_in_menu as user_in_menu
import handlers.save_look as save_look
import api_req_func as api_req_func

from aiogram.filters.callback_data import CallbackData
from aiogram.types import FSInputFile, Message, CallbackQuery

import keyboards
from callback_classes import *

router = Router()

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client[config.db_name]
mongo_fittings = mongo_db['fittings']
# mongo_users = mongo_db['users']

OK = '✅ '
NOK = '❌ '
print('gen')


class GenerateLook(StatesGroup):
    choosing_way_of_generating = State()
    choosing_params = State()
    generation = State()


# ok
@router.message(GenerateLook.choosing_way_of_generating, F.text=='✅ Выбрать параметры')
async def choosing_way_generating(message: types.Message,  state: FSMContext):
    try:
        user_data = await state.get_data()

        # await message.answer(messages.base_clothes, reply_markup=keyboards.get_go_to_menu())
        new_msg = await message.answer('Выберите параметры', reply_markup=keyboards.get_go_to_menu())
        # await new_msg.delete()

        await message.answer_animation(
            animation=file_ids.file_ids['base_clothes'],
            caption=messages.in_generation['prefix'] + messages.in_generation['base_clothes'],
            reply_markup=keyboards.get_button('base_clothes', user_data=user_data)
        )

        await state.update_data({'choosing_params': 'base_clothes'})

        await state.set_state(GenerateLook.choosing_params)
    except Exception as e:
        print(e)
        await save_look.finish(message, state)


async def send_expectation_messages_first(message):
    t = 2
    await message.answer_sticker(file_ids.file_ids['sticker_time'], reply_markup=keyboards.get_go_to_menu())
    await asyncio.sleep(t)


async def send_expectation_messages_second(message, msgs):
    t = 2
    new_msg = await message.answer(msgs[0])
    await asyncio.sleep(t)
    for i in range(1, len(msgs) - 1):
        new_msg = await new_msg.edit_text(msgs[i])
        await asyncio.sleep(t)

    await new_msg.delete()


async def send_expectation_messages_third(message, msgs):
    t = 2
    new_msg = await message.answer(msgs[-1])
    await asyncio.sleep(t)
    
    await new_msg.delete()


@router.message(GenerateLook.choosing_way_of_generating, F.text=='🏠 В меню')
async def callbacks_params_change(message: Message, state: FSMContext):
    # await save_look.finish(message, state)
    await message.answer('Дождитесь окончания примерки (если бот завис вызовите команду /start)')


# ok
@router.message(GenerateLook.choosing_way_of_generating, F.text=='✨ Случайная примерка')
async def random_generation(message: types.Message,  state: FSMContext):
    try:
        # new_msg = await message.answer('Идет случайная примерка', reply_markup=ReplyKeyboardRemove())
        # await new_msg.delete()
        new_msg = await message.answer('Идет случайная примерка', reply_markup=keyboards.get_go_to_menu())
        # await new_msg.delete()

        user_data = await state.get_data()
        random_parameters_list = params_dict.random_parameters[user_data['sex']]
        random_parameters = random.choice(random_parameters_list).replace(' ', '_')
        print(random_parameters)
        
        await state.update_data({'join_parameters': random_parameters})

        await state.set_state(GenerateLook.generation)

        await choosing_generated_look(message, state)
    except Exception as e:
        print(e)
        await save_look.finish(message, state)


# ok
@router.message(GenerateLook.choosing_way_of_generating)
async def choosing_way_generating_incorrectly(message: Message):
    await message.answer(text="Пожалуйста, выберите способ генерации", reply_markup=keyboards.accept_photo())


@router.message(GenerateLook.choosing_params, F.text=='🏠 В меню')
async def callbacks_params_change(message: Message, state: FSMContext):
    await save_look.finish(message, state)
    

@router.callback_query(GenerateLook.choosing_params, F.data=='next')
async def callbacks_params_change(
        callback: types.CallbackQuery,
        state: FSMContext
):
    try:
        user_data = await state.get_data()

        keyb = callback.message.reply_markup
        keyb_len = len(keyb.inline_keyboard) # количество кнопок
        global no_oks
        no_oks = True
        for i in range(keyb_len):
            for j in range(len(keyb.inline_keyboard[i])):
                if keyb.inline_keyboard[i][j].text[0:2] != OK:
                    continue
                else:
                    no_oks = False
        if no_oks:
            await callback.answer(
                text="Выберите хотя бы один параметр",
                show_alert=True
            )
            return

        chat_id = callback.message.chat.id

        param_state = ''
        param_img = ''
        param_button = ''
        # print(user[user['choosing_params']])
        if user_data['choosing_params'] == 'base_clothes':
            if user_data[user_data['choosing_params']] in ['t-shirt', 'shirt', 'blouse']:
                param_state = 'material'
                param_img = 'material'
                param_button = 'material'
            else:
                param_state = 'special_clothes'
                param_img = user_data[user_data['choosing_params']]
                param_button = user_data[user_data['choosing_params']]
        elif user_data['choosing_params'] == 'special_clothes':
            param_state = 'material'
            param_img = 'material'
            param_button = 'material'
        elif user_data['choosing_params'] == 'material':
            param_state = 'color'
            param_img = 'color'
            param_button = 'color'
        elif user_data['choosing_params'] == 'color':
            param_state = 'style'
            param_img = 'style_' + user_data['sex']
            param_button = 'style'
        elif 'style' in user_data['choosing_params']:

            await state.update_data({'choosing_params': param_state})
            
            await callback.message.delete()
            # await send_expectation_messages(callback.message)

            random_parameters_list = [user_data['sex'], user_data['style'], user_data['color'], user_data['material'], user_data['base_clothes']]
            if not user_data['base_clothes'] in ['t-shirt', 'shirt', 'blouse']:
                random_parameters_list.append(user_data['special_clothes'])
                
            random_parameters = '_'.join(random_parameters_list)
            print('random_parameters', random_parameters)
            # print(callback)
            
            await state.update_data({'join_parameters': random_parameters})

            await utils.send_event_to_amplitude(callback.message.chat.id, state, 'param_apply_press')

            await state.set_state(GenerateLook.generation)
            
            await choosing_generated_look(callback.message, state)

            return
        
        await state.update_data({'choosing_params': param_state})
        caption = messages.in_generation['prefix'] + messages.in_generation[param_state]
        animation = types.InputMediaAnimation(media=file_ids.file_ids[param_img], 
                                            caption=caption)
        await callback.message.edit_media(animation)
        await callback.message.edit_caption(
            caption=caption, 
            reply_markup=keyboards.get_button(param_button, user_data=user_data))
    except Exception as e:
        print(e)
        await save_look.finish(callback.message, state)


@router.callback_query(GenerateLook.choosing_params, F.data=='back')
async def callbacks_params_change(
        callback: types.CallbackQuery,
        state: FSMContext
):
    try:
        user_data = await state.get_data()
        chat_id = callback.message.chat.id

        param_state = ''
        param_img = ''
        param_button = ''
        if user_data['choosing_params'] == 'special_clothes':
            param_state = 'base_clothes'
            param_img = 'base_clothes'
            param_button = 'base_clothes'
        elif user_data['choosing_params'] == 'material':
            if user_data['base_clothes'] in ['t-shirt', 'shirt', 'blouse']:
                param_state = 'base_clothes'
                param_img = 'base_clothes'
                param_button = 'base_clothes'
            else:
                param_state = 'special_clothes'
                param_img = user_data['base_clothes']
                param_button = user_data['base_clothes']
        elif user_data['choosing_params'] == 'color':
            param_state = 'material'
            param_img = 'material'
            param_button = 'material'
        elif 'style' in user_data['choosing_params']:
            param_state = 'color'
            param_img = 'color'
            param_button = 'color'
        
        await state.update_data({'choosing_params': param_state})

        caption = messages.in_generation['prefix'] + messages.in_generation[param_state]
        animation = types.InputMediaAnimation(media=file_ids.file_ids[param_img], 
                                            caption=caption)
        await callback.message.edit_media(animation)
        await callback.message.edit_caption(caption=caption, reply_markup=keyboards.get_button(param_button, user_data=user_data))
    except Exception as e:
        print(e)
        await save_look.finish(callback.message, state)


@router.callback_query(GenerateLook.choosing_params, ParamsCallbackFactory.filter())
async def callbacks_params_change(
        callback: types.CallbackQuery, 
        callback_data: ParamsCallbackFactory,
        state: FSMContext
):
    try:
        user_data = await state.get_data()
        print(user_data)
        
        data = user_data['choosing_params'] if user_data['choosing_params'] != 'special_clothes' else user_data['base_clothes']

        if callback_data.state != OK:
            await callback.message.edit_reply_markup(reply_markup=keyboards.get_button(data, user_data=user_data, callback_data=callback_data.data))
        else:
            await callback.message.edit_reply_markup(reply_markup=keyboards.get_button(data, user_data=user_data))
        
        await state.update_data({user_data['choosing_params']: callback_data.data})
    except Exception as e:
        print(e)
        await save_look.finish(callback.message, state)


@router.message(GenerateLook.generation)
async def go_to_menu(message: types.Message, state: FSMContext):
    await message.answer('Дождитесь окончания примерки (если бот завис вызовите команду /start)')
    # await save_look.finish(message, state)


# @router.message(save_look.SaveLook.choosing_generated_look)
# async def go_to_menu_from_save_look(message: types.Message, state: FSMContext):
#     await save_look.finish(message, state)


@router.message(GenerateLook.generation)
async def choosing_generated_look(message: types.Message, state: FSMContext):
    # try:
    user_id = message.chat.id
    user_data = await state.get_data()

    user_in_db = mongo_fittings.find_one({'user_id': user_id})
    print('id', message.chat.id)
    fittings_count = user_in_db['fittings_amount']

    if fittings_count <= 0:
        await utils.send_event_to_amplitude(message.chat.id, state, 'pay_preview_open')

        await save_look.finish(message, state)
        return

    print(user_data)
    work_folder = 'Self-Correction-Human-Parsing'
    prefixes = ['container_generation', 'cont_segmentation', 'output_generation', 'output_segmentation', 'search']
    for prefix in prefixes:
        utils.remove_prefix(f'{work_folder}/{prefix}/' + str(user_id))
    output = []

    random_parameters = user_data['join_parameters']
    print(random_parameters)

    user_id_str = str(user_id)
    src = f"tmps/{user_id_str}.jpg"
    dst = f"{work_folder}/input/{'_'.join([user_id_str, random_parameters, '5'])}.jpg"

    print(src)
    print(dst)
    shutil.copyfile(src, dst)

    await send_expectation_messages_first(message)

    image_path_cont_segmentation_suff = f"{'_'.join([user_id_str, random_parameters])}_5.png"
    image_path_cont_segmentation = f"{work_folder}/cont_segmentation/{image_path_cont_segmentation_suff}"

    print(image_path_cont_segmentation)
    
    new_msg = ''
    while not os.path.isfile(image_path_cont_segmentation):
        print('ok')
        await send_expectation_messages_second(message, messages.generation)
        # await asyncio.sleep(2)
    
    print('in api')
    err = api_req_func.create_request_func(image_path_cont_segmentation_suff, work_folder)
    
    if not err:
        print('Shit')
        await save_look.finish(message, state)
        return
    else:
        for i in range(3):
            print(i)
            image_path = f"{work_folder}/output_generation/{'_'.join([user_id_str, random_parameters, f'5_{i}'])}.png"
            image_path_search = f"{'_'.join([user_id_str, random_parameters, f'5_{i}'])}.png"
            if not os.path.isfile(image_path):
                print('error not file', image_path)
                break
            print(image_path)
            output.append(image_path_search)
            img_url = await utils.upload_image(image_path)
            print(img_url)

            if img_url == '':
                print('error url')
            
            if not os.path.isfile(image_path):
                await send_expectation_messages_third(message, messages.generation)

            # считать количество безошибочных отправок и только тогда кидать в аналитику
            try:
                await message.answer_photo(
                    URLInputFile(img_url),
                    reply_markup=keyboards.choose_look(i)
                )
            except Exception as e:
                print('error when send to telegram')
                print(e)
    
    
    print(output)
    fittings_count -= 1
    print('fittings_count ', fittings_count)

    mongo_fittings.update_one({'user_id': user_id}, {'$set': {"fittings_amount" : fittings_count}})
    await state.update_data({'count': fittings_count})
    await state.update_data({'output': output})

    await message.answer(
        messages.generation_variants, 
        reply_markup=utils.get_reply_kb('generation_variants')
    )
    
    await state.set_state(save_look.SaveLook.choosing_generated_look)

    await utils.send_event_to_amplitude(message.chat.id, state, 'looks_generation_finish')
    # except Exception as e:
    #     print('error in generation')
    #     print(e)
    #     await save_look.finish(message, state)


@router.message(save_look.SaveLook.choosing_generated_look, F.text=='✨ Примерить еще')
async def try_it_on_again(message: types.Message, state: FSMContext):
    try:
        user_id = message.chat.id

        user_in_db = mongo_fittings.find_one({'user_id': user_id})
        print('id', message.chat.id)
        fittings_count = user_in_db['fittings_amount']

        if fittings_count <= 0:
            await user_in_menu.tap_PRO_but(message, state)
            return
        
        await choosing_generated_look(message, state)

    except Exception as e:
        print(e)
        await save_look.finish(message, state)


@router.message(save_look.SaveLook.choosing_generated_look, F.text=='🔄 Начать заново')
async def change_parameters(message: types.Message, state: FSMContext):
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
        await save_look.finish(message, state)