import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from database import (
    update_user_balance, admin_get_all_users, get_user_ip, 
    get_all_cases, get_case_items, get_case_data,
    admin_add_case, admin_del_case, admin_add_item, admin_del_item,
    admin_update_case, admin_update_item,
    add_items_to_inventory_batch, add_keys_to_user, add_specific_item_by_id
)

TOKEN = "8547237995:AAHrUOQInO5b9HVLGbb_2eIlWKIdhzVo86Y"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

def force_dict(item, key_map):
    if item is None: return None
    if hasattr(item, 'keys') or isinstance(item, dict): return dict(item)
    if isinstance(item, (tuple, list)):
        return {key_map[i]: item[i] for i in range(min(len(item), len(key_map)))}
    return item

USER_KEYS = ['id', 'tg_id', 'username', 'balance', 'ip']
CASE_KEYS = ['id', 'name', 'price', 'icon_url']
ITEM_KEYS = ['id', 'name', 'rarity', 'price', 'image_url', 'sound_url', 'case_id']

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    txt = (
        "👨‍💻 <b>ADMIN PANEL v3.0</b>\n\n"
        "<b>Игроки:</b>\n"
        "/users - Список\n"
        "/ip [id] - IP\n"
        "/give [id] [сумма] - Баланс\n"
        "/givecase [user_id] [case_id] [кол-во] - Ключи\n"
        "/giveitem [user_id] [item_id] - Предмет\n\n"
        "<b>Кейсы:</b>\n"
        "/cases - Список\n"
        "/addcase [name] [price] [url]\n"
        "/editcase [id] [name] [price] [url]\n"
        "/delcase [id]\n\n"
        "<b>Предметы:</b>\n"
        "/items [case_id] - Список\n"
        "/additem [case_id] [name] [rarity] [price] [url]\n"
        "/edititem [id] [new_case_id] [name] [rarity] [price] [url]\n"
        "/delitem [id]"
    )
    await message.answer(txt, parse_mode="HTML")

@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    raw_users = await admin_get_all_users()
    users = [force_dict(u, USER_KEYS) for u in raw_users]
    text = "👥 <b>Игроки:</b>\n"
    for u in users:
        text += f"ID: {u['tg_id']} | @{u['username']} | 💰 {u['balance']}\n"
    await message.answer(text[:4000], parse_mode="HTML")

@dp.message(Command("ip"))
async def cmd_ip(message: types.Message):
    try:
        tg_id = int(message.text.split()[1])
        ip = await get_user_ip(tg_id)
        await message.answer(f"🌐 IP игрока {tg_id}: <code>{ip}</code>", parse_mode="HTML")
    except:
        await message.answer("Ошибка. Пиши: /ip 123456")

@dp.message(Command("give"))
async def cmd_give(message: types.Message):
    try:
        _, uid, amt = message.text.split()
        await update_user_balance(int(uid), int(amt))
        await message.answer(f"✅ Выдано {amt} монет игроку {uid}")
    except:
        await message.answer("Ошибка. Пиши: /give 123456 1000")

@dp.message(Command("cases"))
async def cmd_list_cases(message: types.Message):
    raw_cases = await get_all_cases()
    cases = [force_dict(c, CASE_KEYS) for c in raw_cases]
    text = "📦 <b>Кейсы:</b>\n"
    for c in cases:
        text += f"ID: {c['id']} | {c['name']} | {c['price']}р.\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("items"))
async def cmd_list_items(message: types.Message):
    try:
        case_id = int(message.text.split()[1])
        raw_items = await get_case_items(case_id)
        items = [force_dict(i, ITEM_KEYS) for i in raw_items]
        text = f"🔫 <b>Предметы в кейсе {case_id}:</b>\n"
        for i in items:
            text += f"ID: {i['id']} | {i['name']} | {i['rarity']} | {i['price']}\n"
        await message.answer(text[:4000], parse_mode="HTML")
    except:
        await message.answer("Ошибка. Пиши: /items [case_id]")

@dp.message(Command("addcase"))
async def cmd_add_case(message: types.Message):
    try:
        args = message.text.split(maxsplit=3)
        await admin_add_case(args[1], int(args[2]), args[3])
        await message.answer("✅ Кейс добавлен!")
    except:
        await message.answer("Ошибка. Пиши: /addcase [Name] [Price] [Url]")

@dp.message(Command("editcase"))
async def cmd_edit_case(message: types.Message):
    try:
        # /editcase id name price url
        args = message.text.split(maxsplit=4)
        case_id = int(args[1])
        name = args[2]
        price = int(args[3])
        url = args[4]
        
        await admin_update_case(case_id, name, price, url)
        await message.answer(f"✏️ Кейс {case_id} обновлен!")
    except:
        await message.answer("Ошибка. Пиши: /editcase [id] [NewName] [NewPrice] [NewUrl]")

@dp.message(Command("delcase"))
async def cmd_del_case(message: types.Message):
    try:
        case_id = int(message.text.split()[1])
        await admin_del_case(case_id)
        await message.answer("🗑 Кейс удален!")
    except:
        await message.answer("Ошибка. Пиши: /delcase [id]")

@dp.message(Command("additem"))
async def cmd_add_item(message: types.Message):
    try:
        args = message.text.split(maxsplit=5)
        case_id = int(args[1])
        name = args[2]
        rarity = args[3]
        price = int(args[4])
        url = args[5]
        
        await admin_add_item(case_id, name, rarity, price, url)
        await message.answer("✅ Предмет добавлен!")
    except:
        await message.answer("Ошибка. Пиши: /additem [case_id] [name] [rarity] [price] [url]")

@dp.message(Command("edititem"))
async def cmd_edit_item(message: types.Message):
    try:
        # /edititem id new_case_id name rarity price url
        args = message.text.split(maxsplit=6)
        item_id = int(args[1])
        case_id = int(args[2])
        name = args[3]
        rarity = args[4]
        price = int(args[5])
        url = args[6]
        
        await admin_update_item(item_id, case_id, name, rarity, price, url)
        await message.answer(f"✏️ Предмет {item_id} обновлен!")
    except:
        await message.answer("Ошибка. Пиши: /edititem [id] [case_id] [name] [rarity] [price] [url]")

@dp.message(Command("delitem"))
async def cmd_del_item(message: types.Message):
    try:
        item_id = int(message.text.split()[1])
        await admin_del_item(item_id)
        await message.answer("🗑 Предмет удален!")
    except:
        await message.answer("Ошибка. Пиши: /delitem [id]")

@dp.message(Command("givecase"))
async def cmd_give_case(message: types.Message):
    try:
        args = message.text.split()
        user_id = int(args[1])
        case_id = int(args[2])
        count = int(args[3])
        
        if await add_keys_to_user(user_id, case_id, count):
            await message.answer(f"🗝 Выдано {count} ключей от кейса {case_id} игроку {user_id}")
        else:
            await message.answer("❌ Ошибка: Игрок или кейс не найдены.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}\nПиши: /givecase [user_id] [case_id] [count]")

@dp.message(Command("giveitem"))
async def cmd_give_item(message: types.Message):
    try:
        args = message.text.split()
        user_id = int(args[1])
        item_id = int(args[2])
        
        if await add_specific_item_by_id(user_id, item_id):
            await message.answer(f"🎁 Предмет {item_id} выдан игроку {user_id}")
        else:
            await message.answer("❌ Ошибка: Игрок не найден.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}\nПиши: /giveitem [user_id] [item_id]")