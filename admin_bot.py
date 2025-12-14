import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import admin_add_new_item, get_all_cases # Импортируем новую функцию

# --- ТВОИ ДАННЫЕ ---
ADMIN_TOKEN = "8547237995:AAHmdSNHOz9eLu3gfj7OjPky-hW9txmUobA" # ПРОВЕРЕН И В КАВЫЧКАХ
MY_ID = 5208528884 # ТВОЙ АЙДИ

logging.basicConfig(level=logging.INFO)
bot = Bot(token=ADMIN_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Машина состояний для диалога добавления предмета
class AddItem(StatesGroup):
    waiting_for_case = State() # <--- НОВЫЙ ШАГ: Выбор кейса
    waiting_for_name = State()
    waiting_for_rarity = State()
    waiting_for_price = State()
    waiting_for_image = State()
    waiting_for_sound = State() # <--- НОВЫЙ ШАГ: URL звука

def is_admin(message: types.Message):
    return message.from_user.id == MY_ID

@dp.message(Command("add"), is_admin)
async def cmd_add_start(message: types.Message, state: FSMContext):
    cases = await get_all_cases()
    if not cases:
        await message.answer("Сначала создайте кейсы в базе данных.")
        return

    # Создание кнопок для выбора кейса
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=c['name'])] for c in cases],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer("Выберите кейс, в который вы хотите добавить предмет:", reply_markup=keyboard)
    await state.set_state(AddItem.waiting_for_case)
    await state.update_data(cases_data={c['name']: c['id'] for c in cases})

@dp.message(AddItem.waiting_for_case)
async def process_case_choice(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cases_map = data.get('cases_data', {})
    case_name = message.text
    
    if case_name not in cases_map:
        await message.answer("Неверный кейс. Попробуйте снова.")
        return
        
    case_id = cases_map[case_name]
    await state.update_data(case_id=case_id)
    
    await message.answer(f"Выбран кейс: {case_name}. \nВведите название предмета (например, 'Тралалеро Тралала'):", 
                         reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_name)

@dp.message(AddItem.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Common"), types.KeyboardButton(text="Uncommon")],
            [types.KeyboardButton(text="Rare"), types.KeyboardButton(text="Mythical")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Введите редкость:", reply_markup=keyboard)
    await state.set_state(AddItem.waiting_for_rarity)

@dp.message(AddItem.waiting_for_rarity)
async def process_rarity(message: types.Message, state: FSMContext):
    rarity = message.text
    if rarity not in ["Common", "Uncommon", "Rare", "Mythical"]:
        await message.answer("Неверная редкость. Используйте кнопки.")
        return
    await state.update_data(rarity=rarity)
    await message.answer("Введите цену предмета (например, 150):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_price)

@dp.message(AddItem.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        await message.answer("Введите URL картинки предмета (прямая ссылка, https://...):")
        await state.set_state(AddItem.waiting_for_image)
    except ValueError:
        await message.answer("Цена должна быть числом.")

@dp.message(AddItem.waiting_for_image)
async def process_image(message: types.Message, state: FSMContext):
    await state.update_data(image_url=message.text)
    await message.answer("Введите URL ЗВУКА предмета (прямая ссылка на .mp3 или .wav):")
    await state.set_state(AddItem.waiting_for_sound) # <--- НОВЫЙ ШАГ

@dp.message(AddItem.waiting_for_sound)
async def process_sound(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # Полный набор данных
    new_item = {
        'case_id': data['case_id'],
        'name': data['name'],
        'rarity': data['rarity'],
        'price': data['price'],
        'image_url': data['image_url'],
        'sound_url': message.text # <--- СОХРАНЕНИЕ URL ЗВУКА
    }
    
    try:
        await admin_add_new_item(new_item)
        await message.answer(f"✅ Предмет '{new_item['name']}' успешно добавлен в кейс ID {new_item['case_id']}!")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при добавлении в БД: {e}")
        
    await state.clear()

# Вспомогательная функция для БД, которую нужно добавить в database.py
async def admin_add_new_item(item):
    """Добавляет новый предмет в базу данных."""
    import aiosqlite
    import sqlite3
    DB_NAME = "brainrot.db"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item['name'], item['rarity'], item['price'], item['image_url'], item['sound_url'], item['case_id']))
        await db.commit()

# [Остальной код admin_bot.py]
# ...