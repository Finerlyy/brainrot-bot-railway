import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import admin_add_new_item, get_all_cases 

# НОВЫЙ ТОКЕН АДМИНА
ADMIN_TOKEN = "8547237995:AAHy3-r86_noknx1qk0nC8ZmZpERaguURQg" 
# ВАШ ID (ОСТАВЛЯЕМ КАК ЕСТЬ ИЛИ ИЗМЕНЯЕМ ЕСЛИ БОТ ПРИШЛЕТ ДРУГОЙ)
MY_ID = 5208528884 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=ADMIN_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AddItem(StatesGroup):
    waiting_for_case = State() 
    waiting_for_name = State()
    waiting_for_rarity = State()
    waiting_for_price = State()
    waiting_for_image = State()
    waiting_for_sound = State() 

def is_admin(message: types.Message):
    return message.from_user.id == MY_ID

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == MY_ID:
        await message.answer("👋 Привет, Админ! Жми /add чтобы добавить предмет.")
    else:
        await message.answer(f"⛔ Вы не админ.\nВаш ID: `{message.from_user.id}`\nСкопируйте этот ID и вставьте в admin_bot.py в переменную MY_ID.")

@dp.message(Command("cancel"), StateFilter(AddItem))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.")

@dp.message(Command("add"), is_admin)
async def cmd_add_start(message: types.Message, state: FSMContext):
    cases = await get_all_cases()
    if not cases:
        await message.answer("⚠️ Сначала запустите основного бота, чтобы он создал базу данных и кейсы.")
        return

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=c['name'])] for c in cases],
        resize_keyboard=True, one_time_keyboard=True
    )
    
    await message.answer("Выберите кейс:", reply_markup=keyboard)
    await state.set_state(AddItem.waiting_for_case)
    await state.update_data(cases_data={c['name']: c['id'] for c in cases})

@dp.message(AddItem.waiting_for_case)
async def process_case_choice(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cases_map = data.get('cases_data', {})
    if message.text not in cases_map:
        await message.answer("Неверный кейс.")
        return
    await state.update_data(case_id=cases_map[message.text])
    await message.answer("Название предмета?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_name)

@dp.message(AddItem.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="Common"), types.KeyboardButton(text="Uncommon")], [types.KeyboardButton(text="Rare"), types.KeyboardButton(text="Mythical")]], resize_keyboard=True)
    await message.answer("Редкость?", reply_markup=kb)
    await state.set_state(AddItem.waiting_for_rarity)

@dp.message(AddItem.waiting_for_rarity)
async def process_rarity(message: types.Message, state: FSMContext):
    if message.text not in ["Common", "Uncommon", "Rare", "Mythical"]:
        await message.answer("Используйте кнопки.")
        return
    await state.update_data(rarity=message.text)
    await message.answer("Цена (число)?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_price)

@dp.message(AddItem.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Нужно число.")
        return
    await state.update_data(price=int(message.text))
    await message.answer("Ссылка на картинку?")
    await state.set_state(AddItem.waiting_for_image)

@dp.message(AddItem.waiting_for_image)
async def process_image(message: types.Message, state: FSMContext):
    await state.update_data(image_url=message.text)
    await message.answer("Ссылка на звук (.mp3)?")
    await state.set_state(AddItem.waiting_for_sound)

@dp.message(AddItem.waiting_for_sound)
async def process_sound(message: types.Message, state: FSMContext):
    data = await state.get_data()
    new_item = {
        'case_id': data['case_id'], 'name': data['name'], 'rarity': data['rarity'],
        'price': data['price'], 'image_url': data['image_url'], 'sound_url': message.text 
    }
    try:
        await admin_add_new_item(new_item)
        await message.answer(f"✅ Добавлено: {new_item['name']}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    await state.clear()

@dp.message()
async def debug_catch_all(message: types.Message):
    await message.answer(
        f"🤖 Бот работает, но команда не распознана или у вас нет прав.\n"
        f"Ваш ID: `{message.from_user.id}`\n"
        f"В коде прописан ID: `{MY_ID}`"
    )