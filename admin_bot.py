import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import admin_add_new_item

# --- ТВОИ ДАННЫЕ ---
ADMIN_TOKEN = "8547237995:AAHmdSNHOz9eLu3gfj7OjPky-hW9txmUobA" # <-- ПРОВЕРЬ В КАВЫЧКАХ
MY_ID = 5208528884

logging.basicConfig(level=logging.INFO)
bot = Bot(token=ADMIN_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Машина состояний для диалога добавления предмета
class AddItem(StatesGroup):
    waiting_for_name = State()
    waiting_for_rarity = State()
    waiting_for_price = State()
    waiting_for_image = State()

def is_admin(message: types.Message):
    return message.from_user.id == MY_ID

# ... [Дальнейший код не менялся] ...
# (Остальной код admin_bot.py остается как в предыдущем ответе)