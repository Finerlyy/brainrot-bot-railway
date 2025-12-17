import logging
import random
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2
import sqlite3

from database import (
    get_user, get_inventory_grouped, get_leaderboard, get_all_cases, 
    get_case_items, add_items_to_inventory_batch, update_user_balance, 
    get_case_data, sell_items_batch_db, get_all_items_sorted, 
    delete_one_item_by_id, add_item_to_inventory, update_user_ip,
    get_user_keys, use_keys, get_profile_stats, increment_cases_opened,
    update_user_photo, get_public_profile
)

TOKEN = "8292962840:AAHqOus6QIKOhYoYeEXjE4zMGHkGRSR_Ztc" 
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app"
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = web.Application()

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

def force_dict(item, key_map):
    if item is None: return None
    if hasattr(item, 'keys') or isinstance(item, dict): return dict(item)
    if isinstance(item, (tuple, list)):
        return {key_map[i]: item[i] for i in range(min(len(item), len(key_map)))}
    return item

ITEM_KEYS = ['id', 'name', 'rarity', 'price', 'image_url', 'sound_url', 'case_id']
CASE_KEYS = ['id', 'name', 'price', 'icon_url']
USER_KEYS = ['id', 'tg_id', 'username', 'balance', 'ip', 'cases_opened', 'reg_date', 'photo_url']

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await get_user(message.from_user.id, message.from_user.username or "Anon")
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🕹 ОТКРЫТЬ КЕЙСЫ 🎰", web_app=WebAppInfo(url=WEB_APP_URL))]])
    await message.answer("Жми кнопку, чтобы играть!", reply_markup=kb)

async def web_index(request):
    return aiohttp_jinja2.render_template('index.html', request, {'ver': random.randint(1, 99999)})

async def api_get_data(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        
        # IP
        ip_header = request.headers.get('X-Forwarded-For')
        ip = ip_header.split(',')[0].strip() if ip_header else request.remote
        if ip: await update_user_ip(user_id, ip)

        # PHOTO URL (если пришла с фронта)
        photo_url = data.get('photo_url')
        if photo_url: await update_user_photo(user_id, photo_url)

        raw_user = await get_user(user_id, data.get('username'))
        user_data = force_dict(raw_user, USER_KEYS)
        
        stats = await get_profile_stats(user_id)
        user_data['best_item'] = stats.get('best_item')
        user_data['net_worth'] = user_data['balance'] + (stats.get('inv_value') or 0)
        
        INV_KEYS = ['item_id', 'name', 'rarity', 'image_url', 'price', 'quantity']
        raw_inv = await get_inventory_grouped(user_id)
        
        inventory = []
        for item in raw_inv:
            i_dict = force_dict(item, INV_KEYS)
            p = i_dict.get('price', 0)
            r = i_dict.get('rarity', 'Common')
            if r == 'Secret': i_dict['sell_price'] = max(1, int(p * 0.90))
            else: i_dict['sell_price'] = max(1, int(p * 0.60)) 
            inventory.append(i_dict)

        raw_cases = await get_all_cases()
        cases = [force_dict(c, CASE_KEYS) for c in raw_cases]
        
        user_keys = await get_user_keys(user_id)
        for c in cases: c['keys'] = user_keys.get(c['id'], 0)

        raw_all_items = await get_all_items_sorted()
        all_items = [force_dict(i, ITEM_KEYS) for i in raw_all_items]

        return web.json_response({
            "user": user_data, 
            "inventory": inventory, 
            "cases": cases, 
            "leaderboard": await get_leaderboard(),
            "all_items": all_items
        })
    except Exception as e: 
        logging.error(f"Error api_get_data: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

# --- НОВЫЙ РОУТ ДЛЯ ПРОСМОТРА ЧУЖОГО ПРОФИЛЯ ---
async def api_get_profile(request):
    try:
        data = await request.json()
        target_id = int(data.get('target_id'))
        profile = await get_public_profile(target_id)
        
        if profile: return web.json_response({"profile": profile})
        else: return web.json_response({"error": "User not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_open_case(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        case_id = int(data.get('case_id'))
        count = int(data.get('count', 1))
        
        if count > 50: count = 50
        if count < 1: count = 1
        
        raw_case = await get_case_data(case_id)
        case_data = force_dict(raw_case, CASE_KEYS)
        if not case_data: return web.json_response({"error": "Кейс не найден"}, status=404)

        user_keys = await get_user_keys(user_id)
        available_keys = user_keys.get(case_id, 0)
        
        using_keys = False
        if available_keys >= count:
            using_keys = True
            if not await use_keys(user_id, case_id, count):
                return web.json_response({"error": "Ошибка списания ключей"}, status=400)
        else:
            total_price = case_data['price'] * count
            raw_user = await get_user(user_id, 'temp')
            user = force_dict(raw_user, USER_KEYS)
            if user['balance'] < total_price: return web.json_response({"error": "Мало денег!"}, status=400)
            await update_user_balance(user_id, -total_price) 

        raw_items = await get_case_items(case_id)
        items = [force_dict(i, ITEM_KEYS) for i in raw_items]
        if not items: return web.json_response({"error": "Кейс пуст"}, status=400)

        weights = [10000 / (item.get('price', 1) + 1) for item in items]
        dropped = [random.choices(items, weights=weights, k=1)[0] for _ in range(count)]
        
        await add_items_to_inventory_batch(user_id, dropped)
        await increment_cases_opened(user_id, count)
        
        return web.json_response({"dropped": dropped, "used_keys": using_keys})
    except Exception as e: 
        logging.error(f"Error api_open_case: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

async def api_sell_batch(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        item_id = int(data.get('item_id')) 
        count = int(data.get('count'))
        price_per_item = int(data.get('price_per_item'))
        
        total_price = count * price_per_item
        success = await sell_items_batch_db(user_id, item_id, count, total_price)
        
        return web.json_response({"status": "ok"}) if success else web.json_response({"error": "Ошибка"}, status=400)
    except Exception as e: 
        logging.error(f"Error api_sell_batch: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

async def api_upgrade(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        item_id = int(data.get('item_id'))
        target_id = int(data.get('target_id'))
        
        raw_inv = await get_inventory_grouped(user_id)
        INV_KEYS = ['item_id', 'name', 'rarity', 'image_url', 'price', 'quantity']
        inventory = [force_dict(i, INV_KEYS) for i in raw_inv]
        
        my_item = next((i for i in inventory if i['item_id'] == item_id and i['quantity'] > 0), None)
        if not my_item: return web.json_response({"error": "Предмет не найден"}, status=400)
        
        raw_all_items = await get_all_items_sorted()
        all_items = [force_dict(i, ITEM_KEYS) for i in raw_all_items]
        target_item = next((i for i in all_items if i['id'] == target_id), None)
        if not target_item: return web.json_response({"error": "Цель не найдена"}, status=400)

        chance = (my_item['price'] / target_item['price']) * 95
        if chance > 80: chance = 80
        if chance < 1: chance = 1

        await delete_one_item_by_id(user_id, item_id)
        
        roll = random.uniform(0, 100)
        is_win = roll <= chance
        
        item_data = None
        if is_win:
            await add_item_to_inventory(user_id, target_item)
            item_data = target_item
        
        return web.json_response({"status": "win" if is_win else "lose", "item": item_data, "roll": roll, "chance": chance})
    except Exception as e: 
        logging.error(f"Upgrade Error: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

app.add_routes([
    web.get('/', web_index), 
    web.post('/api/data', api_get_data), 
    web.post('/api/profile', api_get_profile), # Новый роут
    web.post('/api/open', api_open_case), 
    web.post('/api/sell_batch', api_sell_batch), 
    web.post('/api/upgrade', api_upgrade), 
    web.static('/static', STATIC_DIR)
])