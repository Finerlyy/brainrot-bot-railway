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
    get_item_by_id, get_case_by_id, admin_update_field,
    get_rarity_weights, set_rarity_weight,
    update_user_brc, admin_get_user_inventory_detailed, admin_update_inventory_mutation
)

# --- НОВЫЙ ТОКЕН АДМИН БОТА ---
TOKEN = "8547237995:AAEj8wYaQUXCWpBpjBC5CQI_pzGgYF4Fpog"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

class EditState(StatesGroup):
    waiting_for_value = State()

def force_dict(item):
    if hasattr(item, 'keys'): return dict(item)
    return item

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    txt = (
        "👨‍💻 <b>ADMIN PANEL v6.0 (Incubator + Edit)</b>\n\n"
        "<b>Игроки:</b>\n"
        "/users, /ip [id], /give [id] [sum]\n"
        "/setcoins [id] [amount] - 🧠 Brainrot Coins\n"
        "/checkinv [id] - Инвентарь с ID предметов\n"
        "/setmut [inv_id] [mut1,mut2] - Изменить мутации\n\n"
        "<b>Дроп:</b>\n"
        "/givecase [user] [case] [num]\n"
        "/giveitem [user] [item]\n"
        "/chances - Шансы\n\n"
        "<b>Редактор (КНОПКИ):</b>\n"
        "/editcase [id] | /edititem [id]\n"
        "/cases | /items [case_id]\n\n"
        "<b>Удаление:</b>\n"
        "/delcase [id] | /delitem [id]"
    )
    await message.answer(txt, parse_mode="HTML")

# --- УПРАВЛЕНИЕ КОИНАМИ И МУТАЦИЯМИ ---
@dp.message(Command("setcoins"))
async def cmd_setcoins(message: types.Message):
    try:
        args = message.text.split()
        user_id = int(args[1])
        amount = int(args[2])
        await update_user_brc(user_id, amount)
        await message.answer(f"✅ Выдано {amount} Brainrot Coins игроку {user_id}")
    except: await message.answer("Ошибка. /setcoins [id] [amount]")

@dp.message(Command("checkinv"))
async def cmd_checkinv(message: types.Message):
    try:
        target_id = int(message.text.split()[1])
        items = await admin_get_user_inventory_detailed(target_id)
        if not items: return await message.answer("Инвентарь пуст.")
        
        text = f"🎒 <b>Инвентарь {target_id}:</b>\n\n"
        for i in items:
            muts = i['mutations'] if i['mutations'] else "Нет"
            text += f"🆔 <code>{i['unique_id']}</code> | <b>{i['name']}</b> ({i['rarity']}) | Мут: {muts}\n"
            if len(text) > 3500:
                await message.answer(text, parse_mode="HTML")
                text = ""
        if text: await message.answer(text, parse_mode="HTML")
    except: await message.answer("Ошибка. /checkinv [user_id]")

@dp.message(Command("setmut"))
async def cmd_setmut(message: types.Message):
    try:
        # /setmut 123 Galaxy,Gold
        args = message.text.split(maxsplit=2)
        inv_id = int(args[1])
        new_muts = args[2] if len(args) > 2 else ""
        
        await admin_update_inventory_mutation(inv_id, new_muts)
        await message.answer(f"✅ Предмет #{inv_id} обновлен. Мутации: {new_muts}")
    except: await message.answer("Ошибка. /setmut [inv_unique_id] [mut1,mut2] (или пусто для сброса)")

# --- УПРАВЛЕНИЕ ШАНСАМИ ---
@dp.message(Command("chances"))
async def cmd_chances(message: types.Message):
    weights = await get_rarity_weights()
    text = "🎲 <b>Веса редкостей (выше = чаще):</b>\n\n"
    for r, w in weights.items():
        text += f"▫️ <b>{r}</b>: {w}\n"
    text += "\n<i>Изменить: /setchance Secret 5</i>"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("setchance"))
async def cmd_setchance(message: types.Message):
    try:
        args = message.text.split()
        rarity = args[1]
        weight = int(args[2])
        await set_rarity_weight(rarity, weight)
        await message.answer(f"✅ Вес для <b>{rarity}</b> установлен на <b>{weight}</b>", parse_mode="HTML")
    except: await message.answer("Ошибка. /setchance [Rarity] [Weight]")

# --- ОСТАЛЬНОЕ (БЕЗ ИЗМЕНЕНИЙ) ---
@dp.message(Command("cases"))
async def cmd_cases(message: types.Message):
    cases = await get_all_cases()
    text = "📦 <b>Кейсы:</b>\n\n"
    for c in cases: text += f"🆔 <code>{c['id']}</code> | <b>{c['name']}</b> | {c['price']}⭐️\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("items"))
async def cmd_items(message: types.Message):
    try:
        case_id = int(message.text.split()[1])
        items = await get_case_items(case_id)
        text = f"🔫 <b>Предметы кейса {case_id}:</b>\n\n"
        for i in items: text += f"🆔 <code>{i['id']}</code> | <b>{i['name']}</b> | {i['rarity']} | {i['price']}⭐️\n"
        await message.answer(text[:4000], parse_mode="HTML")
    except: await message.answer("⚠️ Используй: /items [case_id]")

@dp.message(Command("edititem"))
async def cmd_edit_item_menu(message: types.Message):
    try:
        item_id = int(message.text.split()[1])
        item = await get_item_by_id(item_id)
        if not item: return await message.answer("❌ Предмет не найден")
        item = force_dict(item)
        text = f"🛠 <b>Предмет #{item_id}</b>\nНазвание: {item['name']}\nРедкость: {item['rarity']}\nЦена: {item['price']}\nID Кейса: {item['case_id']}\nКартинка: <a href='{item['image_url']}'>Ссылка</a>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_item:name:{item_id}"), InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_item:price:{item_id}")],
            [InlineKeyboardButton(text="💎 Редкость", callback_data=f"edit_item:rarity:{item_id}"), InlineKeyboardButton(text="🖼 Картинка", callback_data=f"edit_item:image_url:{item_id}")],
            [InlineKeyboardButton(text="📦 ID Кейса", callback_data=f"edit_item:case_id:{item_id}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    except: await message.answer("⚠️ Используй: /edititem [id]")

@dp.message(Command("editcase"))
async def cmd_edit_case_menu(message: types.Message):
    try:
        case_id = int(message.text.split()[1])
        case = await get_case_by_id(case_id)
        if not case: return await message.answer("❌ Кейс не найден")
        case = force_dict(case)
        text = f"🛠 <b>Кейс #{case_id}</b>\nНазвание: {case['name']}\nЦена: {case['price']}\nКартинка: <a href='{case['icon_url']}'>Ссылка</a>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_case:name:{case_id}"), InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_case:price:{case_id}")],
            [InlineKeyboardButton(text="🖼 Картинка", callback_data=f"edit_case:icon_url:{case_id}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    except: await message.answer("⚠️ Используй: /editcase [id]")

@dp.callback_query(F.data.startswith("edit_"))
async def callback_edit(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    table = "items" if parts[0] == "edit_item" else "cases"
    await state.update_data(table=table, field=parts[1], id=parts[2])
    await state.set_state(EditState.waiting_for_value)
    await callback.message.answer(f"✍️ Введите новое значение для <b>{parts[1]}</b>:", parse_mode="HTML")
    await callback.answer()

@dp.message(StateFilter(EditState.waiting_for_value))
async def process_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if await admin_update_field(data['table'], data['id'], data['field'], message.text):
        await message.answer(f"✅ Успешно! {data['field']} -> {message.text}")
    else: await message.answer("❌ Ошибка")
    await state.clear()

@dp.message(Command("addcase"))
async def cmd_add(m: types.Message):
    try: args = m.text.split(maxsplit=3); await admin_add_case(args[1], int(args[2]), args[3]); await m.answer("✅")
    except: await m.answer("Err")

@dp.message(Command("delcase"))
async def cmd_del(m: types.Message):
    try: await admin_del_case(int(m.text.split()[1])); await m.answer("🗑")
    except: await m.answer("Err")

@dp.message(Command("additem"))
async def cmd_addi(m: types.Message):
    try: args = m.text.split(maxsplit=5); await admin_add_item(int(args[1]), args[2], args[3], int(args[4]), args[5]); await m.answer("✅")
    except: await m.answer("Err")

@dp.message(Command("delitem"))
async def cmd_deli(m: types.Message):
    try: await admin_del_item(int(m.text.split()[1])); await m.answer("🗑")
    except: await m.answer("Err")

@dp.message(Command("givecase"))
async def cmd_gk(m: types.Message):
    try: args = m.text.split(); await add_keys_to_user(int(args[1]), int(args[2]), int(args[3])); await m.answer("🗝")
    except: await m.answer("Err")

@dp.message(Command("giveitem"))
async def cmd_gi(m: types.Message):
    try: args = m.text.split(); await add_specific_item_by_id(int(args[1]), int(args[2])); await m.answer("🎁")
    except: await m.answer("Err")

@dp.message(Command("users"))
async def cmd_u(m: types.Message):
    users = await admin_get_all_users()
    t = "👥 <b>Users:</b>\n"; 
    for u in users: t+=f"ID: {u['tg_id']} | {u['username']} | {u['balance']}⭐️ | {u.get('brainrot_coins',0)}🧠\n"
    await m.answer(t[:4000], parse_mode="HTML")

@dp.message(Command("ip"))
async def cmd_ip(m: types.Message):
    try: ip = await get_user_ip(int(m.text.split()[1])); await m.answer(f"IP: {ip}")
    except: await m.answer("Err")

@dp.message(Command("give"))
async def cmd_g(m: types.Message):
    try: args = m.text.split(); await update_user_balance(int(args[1]), int(args[2])); await m.answer("✅")
    except: await m.answer("Err")