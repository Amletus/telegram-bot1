import sqlite3
from aiogram import types, Dispatcher
from datetime import datetime
from states import UserRegistration, TaskCreation, TaskEditing
from database import connect_db, insert_new_task, get_task_details, update_task, delete_task, insert_new_task
from keyboards import main_menu, skip_assistant_keyboard
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Text
from aiogram import Bot
from config import BOT_TOKEN
import asyncio

bot = Bot(token=BOT_TOKEN)

# Підключення до бази даних
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()


async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id

    cursor.execute('SELECT user_id FROM user WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        await bot.send_message(message.from_user.id, "Введіть ваш нікнейм або ім'я для реєстрації:")
        await UserRegistration.waiting_for_nickname.set()
    else:
        await bot.send_message(message.from_user.id, "Вельмишановний, ви вже зареєстровані. Ось головне меню:",
                               reply_markup=main_menu())


async def process_nickname(message: types.Message, state: FSMContext):
    nickname = message.text
    user_id = message.from_user.id
    cursor.execute('INSERT INTO user (user_id, user_name) VALUES (?, ?)', (user_id, nickname))
    conn.commit()
    await state.finish()
    await bot.send_message(message.from_user.id, "🥳🥳🥳Реєстрація завершена. Ви можете створювати собі задачі...",
                           reply_markup=main_menu())


async def create_task(message: types.Message):
    await TaskCreation.waiting_for_name.set()
    await message.reply("Введіть назву задачі:")


async def task_name_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await TaskCreation.next()
    await message.reply("Введіть тип задачі:")


async def task_type_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['type'] = message.text
    await TaskCreation.next()
    await message.reply("Введіть складність задачі (від 1 до 10):")


async def task_complexity_received(message: types.Message, state: FSMContext):
    complexity = message.text
    if complexity.isdigit() and 1 <= int(complexity) <= 10:
        async with state.proxy() as data:
            data['complexity'] = int(complexity)
        await TaskCreation.next()
        await message.reply("⌛Введіть дату дедлайну (формат YYYY-MM-DD):⏳")
    else:
        await message.reply("⛔Будь ласка, введіть число від 1 до 10 для складності задачі:⛔")


async def task_end_date_received(message: types.Message, state: FSMContext):
    end_date = message.text
    try:
        # Перевірка формату дати
        datetime.strptime(end_date, '%Y-%m-%d')
        async with state.proxy() as data:
            data['end_date'] = end_date
        await TaskCreation.next()
        await message.reply("Введіть опис задачі:")
    except ValueError:
        await message.reply("⛔Будь ласка, введіть дату у форматі YYYY-MM-DD:⛔")


async def task_description_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await TaskCreation.next()
    await message.reply("🐵Введіть ID асистента (або натисніть 'Пропустити' якщо в тебе немає з ким хоч щось робити і взагалі ти сам по собі):🐵",
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton('Пропустити', callback_data='skip_assistant')))


async def skip_assistant(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    data = await state.get_data()
    user_id = callback_query.from_user.id

    # Асинхронно не хотіло працювати чогось
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, insert_new_task, user_id, data['name'], data['type'], data['complexity'],
                               data['end_date'], data['description'], None)

    await state.finish()
    await bot.send_message(callback_query.from_user.id, "✅✅✅Проблему успішно створено! Можеш починати її вирішувати, бо ти ж один її вирішуєш...✅✅✅", reply_markup=main_menu())


async def assistant_id_received(message: types.Message, state: FSMContext):
    assistant_id = message.text if message.text.isdigit() else None
    await state.update_data(assistant_id=assistant_id)
    await create_task_in_db(message, state, message.from_user.id)


async def create_task_in_db(message: types.Message, state: FSMContext, user_id):
    async with state.proxy() as data:
        cursor.execute('''INSERT INTO tasks (user, name, type, complexity, end_date, disc, user_assist, closed)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (user_id, data['name'], data['type'], data['complexity'], data['end_date'], data['description'],
                        data['assistant_id'], 0))
        conn.commit()
    await state.finish()
    await bot.send_message(message.from_user.id, "✅✅✅Проблему успішно створено!✅✅✅", reply_markup=main_menu())


# Нові функції Активні задачі та Про мене
async def show_active_tasks(message: types.Message):
    user_id = message.from_user.id
    cursor.execute('SELECT id, name FROM tasks WHERE user=? AND closed=0', (user_id,))
    tasks = cursor.fetchall()
    if tasks:
        for task_id, task_name in tasks:
            task_info = f"Задача: {task_name}\n"
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Деталі", callback_data=f"detail_{task_id}")],
                [InlineKeyboardButton(text="Завершити", callback_data=f"finish_{task_id}")],
                [InlineKeyboardButton(text="Редагувати(не треба, воно не працює)", callback_data=f"edit_{task_id}")],
                [InlineKeyboardButton(text="Видалити", callback_data=f"delete_{task_id}")]
            ])
            await message.answer(task_info, reply_markup=markup)
    else:
        # Якщо активних завдань немає, то хай хоч покаже завершені
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Переглянути завершені завдання", callback_data='view_completed_tasks'))
        await message.answer("Немає активних проблем)).", reply_markup=markup)


async def user_info(message: types.Message):
    user_id = message.from_user.id
    cursor.execute('SELECT user_name FROM user WHERE user_id = ?', (user_id,))
    user_name = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user=? AND closed=0', (user_id,))
    active_tasks_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user=? AND closed=1', (user_id,))
    completed_tasks_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user=?', (user_id,))
    total_tasks_count = cursor.fetchone()[0]

    # СЛАВА УКРАЇНІ!
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Підтримати автора", url="https://send.monobank.ua/jar/6GZHsYbu58"))
    markup.add(InlineKeyboardButton("Підтримати ЗСУ", url="https://send.monobank.ua/jar/A2muaAZwj9"))

    await message.reply(f"ID: {user_id}\n"
                        f"Нікнейм: {user_name}\n"
                        f"Активні задачі: {active_tasks_count}\n"
                        f"Завершені задачі: {completed_tasks_count}\n"
                        f"Усього задач: {total_tasks_count}",
                        reply_markup=markup)


# НЕ ТРОГАТЬ, ПРАЦЮЄ НА СВЯТОМУ СЛОВІ!!!
async def task_detail(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split('_')[1])
    cursor.execute('SELECT name, type, complexity, end_date, disc, user_assist FROM tasks WHERE id=?', (task_id,))
    task = cursor.fetchone()
    if task:
        name, task_type, complexity, end_date, description, user_assist = task
        task_details = (f"Назва: {name}\nТип: {task_type}\nСкладність: {complexity}\n"
                        f"Дедлайн: {end_date}\nОпис: {description}\n Асистент: {user_assist}")
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Завершити!", callback_data=f"finish_{task_id}")],
            [InlineKeyboardButton(text="Редагувати(не треба, воно не працює)", callback_data=f"choose_task_to_edit{task_id}")],
            [InlineKeyboardButton(text="Видалити", callback_data=f"delete_{task_id}")]
        ])
        await bot.send_message(callback_query.from_user.id, task_details, reply_markup=markup)
    else:
        await bot.answer_callback_query(callback_query.id, text="Задачу не знайдено.")
    await bot.answer_callback_query(callback_query.id)


async def finish_task(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split('_')[1])
    cursor.execute('UPDATE tasks SET closed = 1 WHERE id = ?', (task_id,))
    conn.commit()
    await bot.answer_callback_query(callback_query.id, text="Задачу завершено.")
    await bot.send_message(callback_query.from_user.id, "Задачу завершено! Час відпочити...", reply_markup=main_menu())

# Тест редагування
async def new_task_name_received(message: types.Message, state: FSMContext):
    new_name = message.text
    async with state.proxy() as data:
        task_id = data['task_id']


    update_task(task_id, 'name', new_name)
    await message.reply("Назву завдання оновлено.")
    await state.finish()


async def delete_task(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split('_')[1])
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    await bot.answer_callback_query(callback_query.id, text="Задачу видалено.")
    await bot.send_message(callback_query.from_user.id, "Задачу знищенно назавжди!", reply_markup=main_menu())


async def view_completed_tasks(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cursor.execute('SELECT id, name FROM tasks WHERE user=? AND closed=1', (user_id,))
    tasks = cursor.fetchall()
    if tasks:
        response = "Завершені задачі:\n"
        response += '\n'.join([f"{task[0]}: {task[1]}" for task in tasks])
        await bot.send_message(callback_query.from_user.id, response, reply_markup=main_menu())
    else:
        await bot.send_message(callback_query.from_user.id, "У вас немає завершених задач((", reply_markup=main_menu())
    await bot.answer_callback_query(callback_query.id)


async def view_completed_tasks_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cursor.execute('SELECT id, name FROM tasks WHERE user=? AND closed=1', (user_id,))
    tasks = cursor.fetchall()
    if tasks:
        response = "Завершені задачі:\n"
        response += '\n'.join([f"{task[0]}: {task[1]}" for task in tasks])
        await bot.send_message(callback_query.from_user.id, response, reply_markup=main_menu())
    else:
        await bot.send_message(callback_query.from_user.id, "У вас немає завершених задач((", reply_markup=main_menu())
    await bot.answer_callback_query(callback_query.id)
    pass

# Ну я намагався але воно не працює
async def choose_task_to_edit(message: types.Message):
    user_id = message.from_user.id
    cursor.execute('SELECT id, name FROM tasks WHERE user=?', (user_id,))
    tasks = cursor.fetchall()

    markup = InlineKeyboardMarkup()
    for task_id, task_name in tasks:
        markup.add(InlineKeyboardButton(task_name, callback_data=f'choose_attribute_to_edit_{task_id}'))

    await message.reply("Я Ж КАЖУ, ВОНО НЕ ПРАЦЮЄ", reply_markup=markup)


async def choose_attribute_to_edit(callback_query: types.CallbackQuery):
    task_id = callback_query.data.split('_')[1]
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назва", callback_data=f"edit_task_name_{task_id}")],
        [InlineKeyboardButton(text="Тип", callback_data=f"edit_task_type_{task_id}")],
        [InlineKeyboardButton(text="Складність", callback_data=f"edit_task_complexity_{task_id}")],
        [InlineKeyboardButton(text="Дедлайн", callback_data=f"edit_task_end_date_{task_id}")],
        [InlineKeyboardButton(text="Опис", callback_data=f"edit_task_description_{task_id}")],
    ])
    await bot.send_message(callback_query.from_user.id, "Виберіть атрибут для редагування:", reply_markup=markup)


# Редагування 2
async def edit_task_name(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = callback_query.data.split('_')[1]
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditing.waiting_for_task_name)
    await bot.send_message(callback_query.from_user.id, "Введіть нову назву задачі:")


# Тип
async def edit_task_type(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = callback_query.data.split('_')[1]
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditing.waiting_for_task_type)
    await bot.send_message(callback_query.from_user.id, "Введіть новий тип задачі:")


# Складність
async def edit_task_complexity(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = callback_query.data.split('_')[1]
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditing.waiting_for_task_complexity)
    await bot.send_message(callback_query.from_user.id, "Введіть нову складність задачі (від 1 до 10):")


# Дедлайн
async def edit_task_end_date(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = callback_query.data.split('_')[1]
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditing.waiting_for_task_end_date)
    await bot.send_message(callback_query.from_user.id, "Введіть нову дату завершення задачі (формат YYYY-MM-DD):")


# Опис
async def edit_task_description(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = callback_query.data.split('_')[1]
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditing.waiting_for_task_description)
    await bot.send_message(callback_query.from_user.id, "Введіть новий опис задачі:")


async def update_task_attribute(message: types.Message, state: FSMContext):
    new_value = message.text
    data = await state.get_data()
    task_id = data['task_id']

    current_state = await state.get_state()
    if current_state == TaskEditing.waiting_for_task_name.state:
        attribute = 'name'
    elif current_state == TaskEditing.waiting_for_task_type.state:
        attribute = 'type'
    elif current_state == TaskEditing.waiting_for_task_complexity.state:
        attribute = 'complexity'
    elif current_state == TaskEditing.waiting_for_task_end_date.state:
        attribute = 'end_date'
        try:
            # ТУПО КОД З СТАК ОВЕРФЛОУ
            datetime.strptime(new_value, '%Y-%m-%d')
        except ValueError:
            await message.reply("Будь ласка, введіть дату у форматі YYYY-MM-DD:")
            return
    elif current_state == TaskEditing.waiting_for_task_description.state:
        attribute = 'disc'

    update_task(task_id, attribute, new_value)

    await message.reply("Задачу оновлено.")
    await state.finish()


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(send_welcome, commands=['start', 'help'], state='*')
    dp.register_message_handler(process_nickname, state=UserRegistration.waiting_for_nickname)
    dp.register_message_handler(create_task, Text(equals="Створити задачу"), state='*')
    dp.register_message_handler(task_name_received, state=TaskCreation.waiting_for_name)
    dp.register_message_handler(task_type_received, state=TaskCreation.waiting_for_type)
    dp.register_message_handler(task_complexity_received, lambda message: message.text.isdigit(),state=TaskCreation.waiting_for_complexity)
    dp.register_message_handler(task_end_date_received, state=TaskCreation.waiting_for_end_date)
    dp.register_message_handler(task_description_received, state=TaskCreation.waiting_for_description)
    dp.register_callback_query_handler(skip_assistant, lambda c: c.data == 'skip_assistant',state=TaskCreation.waiting_for_assistant)
    dp.register_message_handler(assistant_id_received, state=TaskCreation.waiting_for_assistant)
    dp.register_message_handler(user_info, Text(equals="Про мене"), state='*')
    dp.register_message_handler(show_active_tasks, Text(equals="Активні задачі"), state='*')
    dp.register_callback_query_handler(task_detail, lambda c: c.data and c.data.startswith('detail_'))
    dp.register_callback_query_handler(finish_task, lambda c: c.data and c.data.startswith('finish_'))
    dp.register_callback_query_handler(delete_task, lambda c: c.data and c.data.startswith('delete_'))
    dp.register_callback_query_handler(view_completed_tasks, lambda c: c.data == 'view_completed')
    dp.register_callback_query_handler(view_completed_tasks_callback, text='view_completed_tasks')
    dp.register_message_handler(choose_task_to_edit, commands=['choose_task_to_edit'], state='*')
    dp.register_callback_query_handler(choose_attribute_to_edit, lambda c: c.data and c.data.startswith('choose_attribute_to_edit_'))
    dp.register_callback_query_handler(edit_task_name, lambda c: c.data and c.data.startswith('edit_task_name_'),state='*')
    dp.register_callback_query_handler(edit_task_type, lambda c: c.data and c.data.startswith('edit_task_type_'),state='*')
    dp.register_callback_query_handler(edit_task_complexity,state='*')
    dp.register_callback_query_handler(edit_task_end_date,state='*')
    dp.register_callback_query_handler(edit_task_description,lambda c: c.data and c.data.startswith('edit_task_description_'), state='*')
    dp.register_message_handler(update_task_attribute, state=TaskEditing.waiting_for_task_name)
    dp.register_message_handler(update_task_attribute, state=TaskEditing.waiting_for_task_type)
    dp.register_message_handler(update_task_attribute, state=TaskEditing.waiting_for_task_complexity)
    dp.register_message_handler(update_task_attribute, state=TaskEditing.waiting_for_task_end_date)
    dp.register_message_handler(update_task_attribute, state=TaskEditing.waiting_for_task_description)
