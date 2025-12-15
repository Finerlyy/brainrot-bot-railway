import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import admin_add_new_item, get_all_cases, admin_get_all_users, update_user_balance, get_case_items, admin_update_item_field

ADMIN_TOKEN = "8547237995:AAHy3-r86_noknx1qk0nC8ZmZpERaguURQg"
MY_ID = 5208528884 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=ADMIN_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- States ---
class AddItem(StatesGroup):
    waiting_for_case = State() 
    waiting_for_name = State()
    waiting_for_rarity = State()
    waiting_for_price = State()
    waiting_for_image = State()
    waiting_for_sound = State()

class GiveMoney(StatesGroup):
    waiting_for_id = State()
    waiting_for_amount = State()

class EditItem(StatesGroup):
    waiting_for_case = State()
    waiting_for_item = State()
    waiting_for_field = State()
    waiting_for_value = State()

def is_admin(message: types.Message):
    return message.from_user.id == MY_ID

# --- Main Commands ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_admin(message): return await message.answer(f"Твой ID: {message.from_user.id}")
    await message.answer(
        "🛠 **Админ Панель v2.0**\n\n"
        "➕ /add - Добавить предмет\n"
        "✏️ /edit - Изменить предмет\n"
        "💰 /give - Выдать деньги (звезды)\n"
        "👥 /users - Список игроков\n"
        "❌ /cancel - Отмена"
    )

@dp.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.")

# --- 👥 Список Юзеров ---
@dp.message(Command("users"), is_admin)
async def cmd_users(message: types.Message):
    users = await admin_get_all_users()
    if not users: return await message.answer("Пусто.")
    
    text = "👥 **Список игроков:**\n"
    for u in users[:20]: # Показываем последние 20
        text += f"ID: `{u['tg_id']}` | @{u['username']} | 💰 {u['balance']}\n"
    await message.answer(text)

# --- 💰 Выдача денег ---
@dp.message(Command("give"), is_admin)
async def cmd_give(message: types.Message, state: FSMContext):
    await message.answer("Введи Telegram ID игрока (возьми из /users):")
    await state.set_state(GiveMoney.waiting_for_id)

@dp.message(GiveMoney.waiting_for_id)
async def process_give_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("ID должно быть числом!")
    await state.update_data(target_id=int(message.text))
    await message.answer("Сколько выдать? (можно с минусом чтобы забрать):")
    await state.set_state(GiveMoney.waiting_for_amount)

@dp.message(GiveMoney.waiting_for_amount)
async def process_give_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        data = await state.get_data()
        await update_user_balance(data['target_id'], amount)
        await message.answer(f"✅ Баланс ID {data['target_id']} изменен на {amount}.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    await state.clear()

# --- ✏️ Редактирование ---
@dp.message(Command("edit"), is_admin)
async def cmd_edit(message: types.Message, state: FSMContext):
    cases = await get_all_cases()
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text=c['name'])] for c in cases], resize_keyboard=True)
    await message.answer("В каком кейсе предмет?", reply_markup=kb)
    await state.set_state(EditItem.waiting_for_case)
    await state.update_data(cases={c['name']: c['id'] for c in cases})

@dp.message(EditItem.waiting_for_case)
async def edit_case_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text not in data['cases']: return await message.answer("Выбери кнопку.")
    
    case_id = data['cases'][message.text]
    items = await get_case_items(case_id)
    
    if not items: 
        await state.clear()
        return await message.answer("В кейсе нет предметов.")

    # Список предметов кнопками
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text=f"{i['id']}: {i['name']}")] for i in items], resize_keyboard=True)
    await message.answer("Выбери предмет для изменения:", reply_markup=kb)
    await state.set_state(EditItem.waiting_for_item)

@dp.message(EditItem.waiting_for_item)
async def edit_item_step(message: types.Message, state: FSMContext):
    try:
        item_id = int(message.text.split(':')[0]) # Вытаскиваем ID из текста кнопки
        await state.update_data(item_id=item_id)
        
        kb = types.ReplyKeyboardMarkup(keyboard=[
            [types.KeyboardButton(text="name"), types.KeyboardButton(text="price")],
            [types.KeyboardButton(text="image_url"), types.KeyboardButton(text="sound_url")]
        ], resize_keyboard=True)
        await message.answer("Что меняем?", reply_markup=kb)
        await state.set_state(EditItem.waiting_for_field)
    except:
        await message.answer("Ошибка выбора.")

@dp.message(EditItem.waiting_for_field)
async def edit_field_step(message: types.Message, state: FSMContext):
    if message.text not in ['name', 'price', 'image_url', 'sound_url']:
        return await message.answer("Выбери поле из кнопок.")
    await state.update_data(field=message.text)
    await message.answer(f"Введи новое значение для {message.text}:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(EditItem.waiting_for_value)

@dp.message(EditItem.waiting_for_value)
async def edit_value_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    value = message.text
    
    # Валидация
    if data['field'] == 'price':
        if not value.isdigit(): return await message.answer("Цена должна быть числом!")
        value = int(value)
    
    await admin_update_item_field(data['item_id'], data['field'], value)
    await message.answer("✅ Успешно изменено!")
    await state.clear()

# --- ➕ Добавление с Валидацией ---
@dp.message(Command("add"), is_admin)
async def cmd_add(message: types.Message, state: FSMContext):
    cases = await get_all_cases()
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text=c['name'])] for c in cases], resize_keyboard=True)
    await message.answer("Выбери кейс:", reply_markup=kb)
    await state.set_state(AddItem.waiting_for_case)
    await state.update_data(cases={c['name']: c['id'] for c in cases})

@dp.message(AddItem.waiting_for_case)
async def add_case(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text not in data['cases']: return await message.answer("Выбери кнопку!")
    await state.update_data(case_id=data['cases'][message.text])
    await message.answer("Название предмета?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_name)

@dp.message(AddItem.waiting_for_name)
async def add_name(message: types.Message, state: FSMContext):
    if len(message.text) < 3: return await message.answer("Название слишком короткое!")
    await state.update_data(name=message.text)
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="Common"), types.KeyboardButton(text="Uncommon")], [types.KeyboardButton(text="Rare"), types.KeyboardButton(text="Mythical")]], resize_keyboard=True)
    await message.answer("Редкость?", reply_markup=kb)
    await state.set_state(AddItem.waiting_for_rarity)

@dp.message(AddItem.waiting_for_rarity)
async def add_rarity(message: types.Message, state: FSMContext):
    if message.text not in ["Common", "Uncommon", "Rare", "Mythical"]: return await message.answer("Кнопку нажми!")
    await state.update_data(rarity=message.text)
    await message.answer("Цена (число)?")
    await state.set_state(AddItem.waiting_for_price)

@dp.message(AddItem.waiting_for_price)
async def add_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Только цифры!")
    await state.update_data(price=int(message.text))
    await message.answer("Ссылка на картинку (должна начинаться с http):")
    await state.set_state(AddItem.waiting_for_image)

@dp.message(AddItem.waiting_for_image)
async def add_image(message: types.Message, state: FSMContext):
    if not message.text.startswith('http'): return await message.answer("Некорректная ссылка!")
    await state.update_data(image_url=message.text)
    await message.answer("Ссылка на звук (или отправь '-' если нет):")
    await state.set_state(AddItem.waiting_for_sound)

@dp.message(AddItem.waiting_for_sound)
async def add_sound(message: types.Message, state: FSMContext):
    sound = message.text if message.text != '-' else ''
    data = await state.get_data()
    try:
        await admin_add_new_item({
            'case_id': data['case_id'], 'name': data['name'], 'rarity': data['rarity'],
            'price': data['price'], 'image_url': data['image_url'], 'sound_url': sound
        })
        await message.answer("✅ Предмет добавлен и проверен.")
    except Exception as e:
        await message.answer(f"Ошибка БД: {e}")
    await state.clear()