from aiogram import Bot, Dispatcher, F, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile, CallbackQuery
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callback_classes import *
from params_dict import *


OK = '✅ '
NOK = '❌ '


def make_row_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)


def get_gender_selection_kb():
    kb = [
            [types.KeyboardButton(text='♂ Мужской')],
            [types.KeyboardButton(text='♀ Женский')]
        ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_go_to_menu():
    kb = [[types.KeyboardButton(text='🏠 В меню')]]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_back_uploading_photo():
    kb = [[types.KeyboardButton(text='⬅️ Назад')]]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def next():
    kb = [
        [types.KeyboardButton(text='Завершить 🎉')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_gender_selection():
    kb = [
        [types.KeyboardButton(text='♂ Мужской')],
        [types.KeyboardButton(text='♀ Женский')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def confirm_photo():
    kb = [
        [types.KeyboardButton(text='✅ Оставить')],
        [types.KeyboardButton(text='🔄 Изменить')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def accept_photo():
    kb = [
        [types.KeyboardButton(text='✅ Выбрать параметры')],
        [types.KeyboardButton(text='✨ Случайная примерка')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def parameters():
    kb = [[
        types.InlineKeyboardButton(text="Футболка", callback_data="t-shirt"),
        types.InlineKeyboardButton(text="Блузка", callback_data="blouse")],
        [types.InlineKeyboardButton(text="Рубашка", callback_data="shirt"),
        types.InlineKeyboardButton(text="Куртка", callback_data="jacket")],
        [types.InlineKeyboardButton(text="Джемпер", callback_data="jumper"),
        types.InlineKeyboardButton(text="Кофта", callback_data="sweater")
    ]]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)


def get_button(data, user_data={'sex': 'woman'}, callback_data=''):
    woman_param = ['Блузка']
    sex = user_data['sex']

    d = params_dict[data]

    adjust_list = []
    adjust_flag = 0
    builder = InlineKeyboardBuilder()
    i = 0
    for key, val in d.items():
        if sex == 'man' and key in woman_param:
            continue

        text = key
        state = NOK
        if val == callback_data:
            text = OK + key
            state = OK
        if len(text) < 12:
            if adjust_flag == 1:
                adjust_list.append(2)
                adjust_flag = 0
            else:
                adjust_flag += 1
        else:
            if adjust_flag == 1:
                adjust_list.extend([1, 1])
            else:
                adjust_list.append(1)
            adjust_flag = 0

        builder.button(
            text=text,
            callback_data=ParamsCallbackFactory(index=i,
                                                data=val,
                                                state=state)
        )
        i += 1

    if adjust_flag == 1:
        adjust_list.append(1)

    back_button = types.InlineKeyboardButton(text='Назад', callback_data='back')
    next_button = types.InlineKeyboardButton(text='Далее ➡️', callback_data='next')
    apply_button = types.InlineKeyboardButton(text='✨ Применить', callback_data='next')

    # по одной кнопке в строку
    # builder.adjust(1)
    if data == 'base_clothes':
        menu = 1
    elif data == 'style':
        menu = 3
    else:
        menu = 2

    if menu == 1:
        builder.add(next_button)
        adjust_list.append(1)
    elif menu == 2:
        builder.add(back_button).add(next_button)
        adjust_list.append(2)
    elif menu == 3:
        builder.add(back_button).add(apply_button)
        adjust_list.append(2)
    
    # print(adjust_list)
    builder.adjust(*adjust_list)

    return builder.as_markup()

def apply():
    kb = [
        [types.KeyboardButton(text='Применить')],
        [types.KeyboardButton(text='Назад')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def params_kb():
    kb = [
        [types.KeyboardButton(text='Далее ➡️')], 
        [types.KeyboardButton(text='Назад')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    

def styles():
    kb = [
        [types.KeyboardButton(text='Стиль -'), types.KeyboardButton(text='Стиль -')],
        [types.KeyboardButton(text='Стиль -'), types.KeyboardButton(text='Стиль -')],
        [types.KeyboardButton(text='✨ Применить')],
        [types.KeyboardButton(text='Назад')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_welcome_screen(pro):
    print('rr')
    kb = []
    if pro == 'false':
        kb = [
            [types.KeyboardButton(text='✨ Создать образ'), types.KeyboardButton(text='💯 Пополнить примерки')],
            [types.KeyboardButton(text='Изменить пол'), types.KeyboardButton(text='Изменить ваше фото')]
        ]
    else:
        kb = [
            [types.KeyboardButton(text='✨ Создать образ')],
            [types.KeyboardButton(text='Изменить пол'), types.KeyboardButton(text='Изменить ваше фото')]
        ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        

def choose_look(index):
# def choose_look(builder):
    kb = [
        [
            types.InlineKeyboardButton(text="❌ Не нравится", callback_data=f"nok_{index}"),
            types.InlineKeyboardButton(text="✅ Выбрать", callback_data=f"ok_{index}")
        ]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

    # builder.add(types.InlineKeyboardButton(
    #     text="✅ Выбрать и далее",
    #     callback_data="ok")
    # )
    # builder.add(types.InlineKeyboardButton(
    #     text="❌ Не нравится",
    #     callback_data="nok")
    # )
    # return builder.as_markup()


def save_look(url):
    kb = [
        [types.InlineKeyboardButton(text="Посмотреть в магазине", url=url)],
        # [types.InlineKeyboardButton(text="Сохранить", callback_data="save")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)


def finish():
    print('e')
    kb = [
        # [types.KeyboardButton(text='Сохранить и поделиться')],
        [types.KeyboardButton(text='🔄 Еще образ'), types.KeyboardButton(text='🏠 В меню')]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def go_to_pro():
    kb = [
        [types.InlineKeyboardButton(text='Пополнить баланс', url="https://forms.gle/sE1bNyEEopwDxkvn6")],
        [types.InlineKeyboardButton(text='Получить бесплатно', url="https://forms.gle/CS8g4QrTQXuYgKCJ6")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)
