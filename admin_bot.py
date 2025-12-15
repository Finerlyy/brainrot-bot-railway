import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import admin_add_new_item, get_all_cases 

ADMIN_TOKEN = "8547237995:AAHy3-r86_noknx1qk0nC8ZmZpERaguURQg"
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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == MY_ID:
        await message.answer(f"Админ ID подтвержден ({MY_ID}).\nЖми /add для добавления предмета.")
    else:
        await message.answer(f"Ты не админ. Твой ID: `{message.from_user.id}`")

@dp.message(Command("cancel"), StateFilter(AddItem))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.")

@dp.message(Command("add"), is_admin)
async def cmd_add(message: types.Message, state: FSMContext):
    cases = await get_all_cases()
    if not cases:
        await message.answer("Нет кейсов в БД.")
        return
    
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text=c['name'])] for c in cases], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("В какой кейс добавляем?", reply_markup=kb)
    await state.set_state(AddItem.waiting_for_case)
    await state.update_data(cases_data={c['name']: c['id'] for c in cases})

@dp.message(AddItem.waiting_for_case)
async def step_case(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text not in data['cases_data']:
        await message.answer("Выбери кнопку.")
        return
    await state.update_data(case_id=data['cases_data'][message.text])
    await message.answer("Название предмета?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_name)

@dp.message(AddItem.waiting_for_name)
async def step_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="Common"), types.KeyboardButton(text="Uncommon")], [types.KeyboardButton(text="Rare"), types.KeyboardButton(text="Mythical")]], resize_keyboard=True)
    await message.answer("Редкость?", reply_markup=kb)
    await state.set_state(AddItem.waiting_for_rarity)

@dp.message(AddItem.waiting_for_rarity)
async def step_rarity(message: types.Message, state: FSMContext):
    if message.text not in ["Common", "Uncommon", "Rare", "Mythical"]:
        return await message.answer("Используй кнопки!")
    await state.update_data(rarity=message.text)
    await message.answer("Цена (число)?", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddItem.waiting_for_price)

@dp.message(AddItem.waiting_for_price)
async def step_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Число!")
    await state.update_data(price=int(message.text))
    await message.answer("Ссылка на картинку (https://...)?")
    await state.set_state(AddItem.waiting_for_image)

@dp.message(AddItem.waiting_for_image)
async def step_image(message: types.Message, state: FSMContext):
    await state.update_data(image_url=message.text)
    await message.answer("Ссылка на звук (.mp3)?")
    await state.set_state(AddItem.waiting_for_sound)

@dp.message(AddItem.waiting_for_sound)
async def step_sound(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        await admin_add_new_item({
            'case_id': data['case_id'], 'name': data['name'], 'rarity': data['rarity'],
            'price': data['price'], 'image_url': data['image_url'], 'sound_url': message.text
        })
        await message.answer("✅ Добавлено!")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    await state.clear()