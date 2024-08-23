from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Створити задачу"),
               KeyboardButton("Активні задачі"),
               KeyboardButton("Про мене"))
    return markup


def skip_assistant_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Пропустити', callback_data='skip_assistant'))
    return markup
