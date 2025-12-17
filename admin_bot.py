import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    update_user_balance, admin_get_all_users, get_user_ip, 
    get_all_cases, get_case_items, 
    admin_add_case, admin_del_case, admin_add_item, admin_del_item,
    add_keys_to_user, add_specific_item_by_id,
    get_item_by_id, get_case_by_id, admin_update_field
)

TOKEN = "8547237995:AAHrUOQInO5b9HVLGbb_2eIlWKIdhzVo86Y"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- МАШИНА СОСТОЯНИЙ (FSM) ---
class EditState(StatesGroup):
    waiting_for_value = State()

# --- HELPER ---
def force_dict(item):
    if hasattr(item, 'keys'): return dict(item)
    return item

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    txt = (
        "👨‍💻 <b>ADMIN PANEL v4.0 (Interactive)</b>\n\n"
        "<b>Управление игроками:</b>\n"
        "/users, /ip [id], /give [id] [sum]\n"
        "/givecase [user] [case] [num] - Ключи\n"
        "/giveitem [user] [item] - Предмет\n\n"
        "<b>Редактор (КНОПКИ):</b>\n"
        "/editcase [id] - Изменить кейс\n"
        "/edititem [id] - Изменить предмет\n\n"
        "<b>Списки:</b>\n"
        "/cases - Все кейсы\n"
        "/items [case_id] - Предметы в кейсе\n\n"
        "<b>Добавить/Удалить (Быстро):</b>\n"
        "/addcase [name] [price] [url]\n"
        "/delcase [id]\n"
        "/additem [case_id] [name] [rarity] [price] [url]\n"
        "/delitem [id]"
    )
    await message.answer(txt, parse_mode="HTML")

# --- ПРОСМОТР СПИСКОВ ---
@dp.message(Command("cases"))
async def cmd_cases(message: types.Message):
    cases = await get_all_cases()
    text = "📦 <b>Кейсы:</b>\n\n"
    for c in cases:
        text += f"🆔 <code>{c['id']}</code> | <b>{c['name']}</b> | {c['price']}⭐️\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("items"))
async def cmd_items(message: types.Message):
    try:
        case_id = int(message.text.split()[1])
        items = await get_case_items(case_id)
        text = f"🔫 <b>Предметы кейса {case_id}:</b>\n\n"
        for i in items:
            text += f"🆔 <code>{i['id']}</code> | <b>{i['name']}</b> | {i['rarity']} | {i['price']}⭐️\n"
        await message.answer(text[:4000], parse_mode="HTML")
    except:
        await message.answer("⚠️ Используй: /items [case_id]")

# --- ИНТЕРАКТИВНОЕ РЕДАКТИРОВАНИЕ ПРЕДМЕТА ---
@dp.message(Command("edititem"))
async def cmd_edit_item_menu(message: types.Message):
    try:
        item_id = int(message.text.split()[1])
        item = await get_item_by_id(item_id)
        if not item: return await message.answer("❌ Предмет не найден")
        
        item = force_dict(item)
        text = (
            f"🛠 <b>Редактор предмета #{item_id}</b>\n"
            f"Название: {item['name']}\n"
            f"Редкость: {item['rarity']}\n"
            f"Цена: {item['price']}\n"
            f"ID Кейса: {item['case_id']}\n"
            f"Картинка: <a href='{item['image_url']}'>Ссылка</a>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_item:name:{item_id}"),
             InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_item:price:{item_id}")],
            [InlineKeyboardButton(text="💎 Редкость", callback_data=f"edit_item:rarity:{item_id}"),
             InlineKeyboardButton(text="🖼 Картинка", callback_data=f"edit_item:image_url:{item_id}")],
            [InlineKeyboardButton(text="📦 ID Кейса", callback_data=f"edit_item:case_id:{item_id}")]
        ])
        
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    except:
        await message.answer("⚠️ Используй: /edititem [id]")

# --- ИНТЕРАКТИВНОЕ РЕДАКТИРОВАНИЕ КЕЙСА ---
@dp.message(Command("editcase"))
async def cmd_edit_case_menu(message: types.Message):
    try:
        case_id = int(message.text.split()[1])
        case = await get_case_by_id(case_id)
        if not case: return await message.answer("❌ Кейс не найден")
        
        case = force_dict(case)
        text = (
            f"🛠 <b>Редактор кейса #{case_id}</b>\n"
            f"Название: {case['name']}\n"
            f"Цена: {case['price']}\n"
            f"Картинка: <a href='{case['icon_url']}'>Ссылка</a>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_case:name:{case_id}"),
             InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_case:price:{case_id}")],
            [InlineKeyboardButton(text="🖼 Картинка", callback_data=f"edit_case:icon_url:{case_id}")]
        ])
        
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    except:
        await message.answer("⚠️ Используй: /editcase [id]")

# --- ОБРАБОТКА НАЖАТИЯ КНОПОК ---
@dp.callback_query(F.data.startswith("edit_"))
async def callback_edit(callback: types.CallbackQuery, state: FSMContext):
    # data format: edit_type:field:id (e.g. edit_item:price:5)
    parts = callback.data.split(":")
    edit_type = parts[0] # edit_item or edit_case
    field = parts[1]
    target_id = parts[2]
    
    table = "items" if edit_type == "edit_item" else "cases"
    
    # Сохраняем во временное хранилище, что мы редактируем
    await state.update_data(table=table, field=field, id=target_id)
    await state.set_state(EditState.waiting_for_value)
    
    await callback.message.answer(f"✍️ Введите новое значение для <b>{field}</b>:", parse_mode="HTML")
    await callback.answer()

# --- ПОЛУЧЕНИЕ НОВОГО ЗНАЧЕНИЯ ---
@dp.message(StateFilter(EditState.waiting_for_value))
async def process_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    new_value = message.text
    
    # Обновляем в БД
    success = await admin_update_field(data['table'], data['id'], data['field'], new_value)
    
    if success:
        await message.answer(f"✅ Успешно! Поле <b>{data['field']}</b> обновлено на: {new_value}", parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка обновления БД.")
        
    await state.clear()

# --- ОСТАЛЬНЫЕ КОМАНДЫ (ADD/DEL/GIVE) ---
@dp.message(Command("addcase"))
async def cmd_add(m: types.Message):
    try:
        args = m.text.split(maxsplit=3)
        await admin_add_case(args[1], int(args[2]), args[3])
        await m.answer("✅ Добавлено!")
    except: await m.answer("Err: /addcase [name] [price] [url]")

@dp.message(Command("delcase"))
async def cmd_del(m: types.Message):
    try: await admin_del_case(int(m.text.split()[1])); await m.answer("🗑 Удалено!")
    except: await m.answer("Err: /delcase [id]")

@dp.message(Command("additem"))
async def cmd_addi(m: types.Message):
    try:
        args = m.text.split(maxsplit=5)
        await admin_add_item(int(args[1]), args[2], args[3], int(args[4]), args[5])
        await m.answer("✅ Предмет добавлен!")
    except: await m.answer("Err: /additem [case_id] [name] [rarity] [price] [url]")

@dp.message(Command("delitem"))
async def cmd_deli(m: types.Message):
    try: await admin_del_item(int(m.text.split()[1])); await m.answer("🗑 Удалено!")
    except: await m.answer("Err: /delitem [id]")

@dp.message(Command("givecase"))
async def cmd_gk(m: types.Message):
    try:
        args = m.text.split()
        await add_keys_to_user(int(args[1]), int(args[2]), int(args[3]))
        await m.answer("🗝 Ключи выданы!")
    except: await m.answer("Err: /givecase [user] [case] [count]")

@dp.message(Command("giveitem"))
async def cmd_gi(m: types.Message):
    try:
        args = m.text.split()
        await add_specific_item_by_id(int(args[1]), int(args[2]))
        await m.answer("🎁 Предмет выдан!")
    except: await m.answer("Err: /giveitem [user] [item]")

@dp.message(Command("users"))
async def cmd_u(m: types.Message):
    users = await admin_get_all_users()
    t = "👥 <b>Users:</b>\n"
    for u in users: t+=f"ID: {u['tg_id']} | {u['username']} | {u['balance']}\n"
    await m.answer(t[:4000], parse_mode="HTML")

@dp.message(Command("ip"))
async def cmd_ip(m: types.Message):
    try:
        ip = await get_user_ip(int(m.text.split()[1]))
        await m.answer(f"IP: {ip}")
    except: await m.answer("Err: /ip [id]")

@dp.message(Command("give"))
async def cmd_g(m: types.Message):
    try:
        args = m.text.split()
        await update_user_balance(int(args[1]), int(args[2]))
        await m.answer("✅ Баланс выдан")
    except: await m.answer("Err")