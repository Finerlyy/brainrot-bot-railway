import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import admin_add_new_item

# --- ТВОИ ДАННЫЕ ---
ADMIN_TOKEN = "8547237995:AAHmdSNHOz9eLu3gfj7OjPky-hW9txmUobA"
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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_admin(message): return
    await message.answer("👋 Привет, Админ!\n\nКоманды:\n/add - Добавить новый предмет в кейс")

@dp.message(Command("add"))
async def start_add(message: types.Message, state: FSMContext):
    if not is_admin(message): return
    await message.answer("1️⃣ Введи НАЗВАНИЕ предмета (например: Ohio Tiramisu):")
    await state.set_state(AddItem.waiting_for_name)

@dp.message(StateFilter(AddItem.waiting_for_name))
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="Common"), types.KeyboardButton(text="Uncommon")],
        [types.KeyboardButton(text="Rare"), types.KeyboardButton(text="Epic"), types.KeyboardButton(text="Legendary")]
    ], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("2️⃣ Выбери РЕДКОСТЬ:", reply_markup=kb)
    await state.set_state(AddItem.waiting_for_rarity)

@dp.message(StateFilter(AddItem.waiting_for_rarity))
async def process_rarity(message: types.Message, state: FSMContext):
    if message.text not in ["Common", "Uncommon", "Rare", "Epic", "Legendary"]:
         await message.answer("❌ Используй кнопки для выбора редкости!")
         return
    await state.update_data(rarity=message.text)
    await message.answer("3️⃣ Введи ЦЕНУ в звездах (число):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_price)

@dp.message(StateFilter(AddItem.waiting_for_price))
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Это не число. Введи число!")
        return
    await state.update_data(price=int(message.text))
    await message.answer("4️⃣ Пришли ССЫЛКУ на картинку (JPEG/PNG).")
    await state.set_state(AddItem.waiting_for_image)

@dp.message(StateFilter(AddItem.waiting_for_image))
async def process_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    image_url = message.text
    
    await admin_add_new_item(data['name'], data['rarity'], data['price'], image_url)
    
    await message.answer(
        f"✅ **ГОТОВО! Предмет добавлен!**\n\n"
        f"📦 {data['name']}\n💎 {data['rarity']}\n⭐️ {data['price']}\n🖼 [Картинка]({image_url})",
        parse_mode="Markdown"
    )
    await state.clear()