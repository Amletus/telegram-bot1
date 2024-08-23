from aiogram.dispatcher.filters.state import State, StatesGroup

class UserRegistration(StatesGroup):
    waiting_for_nickname = State()

class TaskCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_complexity = State()
    waiting_for_end_date = State()
    waiting_for_description = State()
    waiting_for_assistant = State()

class TaskEditing(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_type = State()
    waiting_for_new_value = State()
    waiting_for_task_name = State()
    waiting_for_task_type = State()
    waiting_for_task_complexity = State()
    waiting_for_task_end_date = State()
    waiting_for_task_description = State()
