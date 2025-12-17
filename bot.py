import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2
import sqlite3

# Импортируем функции БД
from database import (
    get_user, get_inventory_grouped, get_leaderboard, get_all_cases, 
    get_case_items, add_items_to_inventory_batch, update_user_balance, 
    get_case_data, sell_items_batch_db, get_all_items_sorted, 
    delete_one_item_by_id, add_item_to_inventory
)

# --- КОНФИГУРАЦИЯ ---
# Вставь свой токен
TOKEN = "8292962840:AAHqOus6QIKOhYoYeEXjE4zMGHkGRSR_Ztc" 
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app"
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = web.Application()

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

# --- ФУНКЦИЯ СПАСЕНИЯ ОТ ОШИБОК TUPLE ---
def force_dict(item, key_map):
    """
    Принудительно превращает результат БД в словарь.
    Работает и с sqlite3.Row, и с dict, и с tuple.
    """
    if item is None:
        return None
    
    # Если это уже словарь или похоже на него (Row)
    if hasattr(item, 'keys') or isinstance(item, dict):
        return dict(item)
    
    # Если это кортеж (tuple) или список -> мапим вручную по ключам
    if isinstance(item, (tuple, list)):
        # Создаем словарь, сопоставляя ключи по порядку
        # Мы используем min, чтобы не упасть, если длина не совпадает
        return {key_map[i]: item[i] for i in range(min(len(item), len(key_map)))}
    
    return item

# Ключи таблиц (порядок важен! он должен совпадать с порядком колонок в БД)
# Таблица items: id, name, rarity, price, image_url, sound_url, case_id
ITEM_KEYS = ['id', 'name', 'rarity', 'price', 'image_url', 'sound_url', 'case_id']
# Таблица cases: id, name, price, icon_url
CASE_KEYS = ['id', 'name', 'price', 'icon_url']
# Таблица users: id, tg_id, username, balance
USER_KEYS = ['id', 'tg_id', 'username', 'balance']

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await get_user(message.from_user.id, message.from_user.username or "Anon")
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🕹 ОТКРЫТЬ КЕЙСЫ 🎰", web_app=WebAppInfo(url=WEB_APP_URL))]])
    await message.answer("Жми кнопку, чтобы играть!", reply_markup=kb)

# --- API ---

async def web_index(request):
    return aiohttp_jinja2.render_template('index.html', request, {'ver': random.randint(1, 99999)})

async def api_get_data(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        
        # 1. User
        raw_user = await get_user(user_id, data.get('username'))
        user_data = force_dict(raw_user, USER_KEYS)
        
        # 2. Inventory (Grouped)
        # Порядок в get_inventory_grouped: item_id, name, rarity, image_url, price, quantity
        INV_KEYS = ['item_id', 'name', 'rarity', 'image_url', 'price', 'quantity']
        raw_inv = await get_inventory_grouped(user_id)
        
        inventory = []
        for item in raw_inv:
            i_dict = force_dict(item, INV_KEYS)
            p, r = i_dict.get('price', 0), i_dict.get('rarity', 'Common')
            
            # Логика цен продажи
            sell = int(p*0.15) if r=='Common' else int(p*0.4) if r=='Uncommon' else int(p*1.1) if r=='Rare' else int(p*3.5)
            i_dict['sell_price'] = max(1, sell)
            inventory.append(i_dict)

        # 3. Cases
        raw_cases = await get_all_cases()
        cases = [force_dict(c, CASE_KEYS) for c in raw_cases]
        
        # 4. Items
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

async def api_open_case(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        case_id = int(data.get('case_id'))
        count = int(data.get('count', 1))
        
        # 1. Получаем Кейс
        raw_case = await get_case_data(case_id)
        case_data = force_dict(raw_case, CASE_KEYS)
        
        if not case_data:
             return web.json_response({"error": "Кейс не найден"}, status=404)

        total_price = case_data['price'] * count
        
        # 2. Получаем Юзера
        raw_user = await get_user(user_id, 'temp')
        user = force_dict(raw_user, USER_KEYS)

        if user['balance'] < total_price: 
            return web.json_response({"error": "Мало денег!"}, status=400)

        # 3. Получаем Предметы (ИСПРАВЛЕНИЕ ОШИБКИ)
        raw_items = await get_case_items(case_id)
        
        # Принудительная конвертация каждого предмета
        items = [force_dict(i, ITEM_KEYS) for i in raw_items]

        if not items:
            return web.json_response({"error": "Кейс пуст"}, status=400)

        # 4. Выбор дропа
        # Теперь items точно список словарей, и item['price'] сработает
        weights = [10000 / (item.get('price', 1) + 1) for item in items]
        dropped = [random.choices(items, weights=weights, k=1)[0] for _ in range(count)]
        
        await update_user_balance(user_id, -total_price) 
        await add_items_to_inventory_batch(user_id, dropped)
        
        return web.json_response({"dropped": dropped})

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
        
        if success:
            return web.json_response({"status": "ok"}) 
        else:
            return web.json_response({"error": "Ошибка продажи"}, status=400)
    except Exception as e: 
        logging.error(f"Error api_sell_batch: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

async def api_upgrade(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        item_id = int(data.get('item_id'))
        target_id = int(data.get('target_id'))
        
        # 1. Получаем инвентарь (безопасно)
        raw_inv = await get_inventory_grouped(user_id)
        INV_KEYS = ['item_id', 'name', 'rarity', 'image_url', 'price', 'quantity']
        
        inventory = [force_dict(i, INV_KEYS) for i in raw_inv]
        
        my_item = next((i for i in inventory if i['item_id'] == item_id and i['quantity'] > 0), None)
        if not my_item: 
            return web.json_response({"error": "Предмет не найден"}, status=400)
        
        # 2. Получаем все предметы (безопасно)
        raw_all_items = await get_all_items_sorted()
        all_items = [force_dict(i, ITEM_KEYS) for i in raw_all_items]
        
        target_item = next((i for i in all_items if i['id'] == target_id), None)
        if not target_item:
            return web.json_response({"error": "Цель не найдена"}, status=400)

        # 3. Шанс
        chance = (my_item['price'] / target_item['price']) * 95
        if chance > 80: chance = 80
        if chance < 1: chance = 1

        # 4. Сжигаем и крутим
        await delete_one_item_by_id(user_id, item_id)
        
        roll = random.uniform(0, 100)
        is_win = roll <= chance
        
        item_data = None
        if is_win:
            await add_item_to_inventory(user_id, target_item)
            item_data = target_item
        
        return web.json_response({
            "status": "win" if is_win else "lose", 
            "item": item_data,
            "roll": roll,
            "chance": chance
        })
    except Exception as e: 
        logging.error(f"Upgrade Error: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)

app.add_routes([
    web.get('/', web_index), 
    web.post('/api/data', api_get_data), 
    web.post('/api/open', api_open_case), 
    web.post('/api/sell_batch', api_sell_batch), 
    web.post('/api/upgrade', api_upgrade), 
    web.static('/static', STATIC_DIR)
])