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
TOKEN = "8292962840:AAHqOus6QIKOhYoYeEXjE4zMGHkGRSR_Ztc" 
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app"
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = web.Application()

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (FIX TUPLE ERROR) ---
# Эти ключи нужны, если база вернет кортежи вместо словарей
USER_KEYS = ['id', 'tg_id', 'username', 'balance']
CASE_KEYS = ['id', 'name', 'price', 'icon_url']
ITEM_KEYS = ['id', 'name', 'rarity', 'price', 'image_url', 'sound_url', 'case_id']

def to_dict(obj, keys):
    """Превращает объект (Row или Tuple) в словарь."""
    if not obj: return None
    if isinstance(obj, dict): return obj
    try:
        # Попытка 1: Если это sqlite3.Row, оно само умеет в dict
        return dict(obj)
    except:
        # Попытка 2: Если это tuple, мапим вручную по ключам
        return dict(zip(keys, obj))

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
        
        # Получаем данные и конвертируем
        raw_user = await get_user(user_id, data.get('username'))
        user_data = to_dict(raw_user, USER_KEYS)
        
        # Инвентарь (тут сложный запрос, ключи свои)
        INV_KEYS = ['item_id', 'name', 'rarity', 'image_url', 'price', 'quantity']
        raw_inv = await get_inventory_grouped(user_id)
        
        inventory = []
        for item in raw_inv:
            i_dict = to_dict(item, INV_KEYS)
            p, r = i_dict['price'], i_dict['rarity']
            # Логика цен
            sell = int(p*0.15) if r=='Common' else int(p*0.4) if r=='Uncommon' else int(p*1.1) if r=='Rare' else int(p*3.5)
            i_dict['sell_price'] = max(1, sell)
            inventory.append(i_dict)

        # Кейсы и Лидерборд
        raw_cases = await get_all_cases()
        cases = [to_dict(c, CASE_KEYS) for c in raw_cases]
        
        # Items sorted
        raw_all_items = await get_all_items_sorted()
        all_items = [to_dict(i, ITEM_KEYS) for i in raw_all_items]

        return web.json_response({
            "user": user_data, 
            "inventory": inventory, 
            "cases": cases, 
            "leaderboard": await get_leaderboard(), # Тут простой dict
            "all_items": all_items
        })
    except Exception as e: 
        logging.error(f"Error api_get_data: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_open_case(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        case_id = int(data.get('case_id'))
        count = int(data.get('count', 1))
        
        # 1. Получаем кейс (Защита от tuple)
        raw_case = await get_case_data(case_id)
        case_data = to_dict(raw_case, CASE_KEYS)
        
        if not case_data:
             return web.json_response({"error": "Кейс не найден"}, status=404)

        total_price = case_data['price'] * count
        
        # 2. Получаем юзера (Защита от tuple)
        raw_user = await get_user(user_id, 'temp')
        user = to_dict(raw_user, USER_KEYS)

        if user['balance'] < total_price: 
            return web.json_response({"error": "Мало денег!"}, status=400)

        # 3. Получаем предметы (Защита от tuple)
        raw_items = await get_case_items(case_id)
        items = [to_dict(i, ITEM_KEYS) for i in raw_items]

        if not items:
            return web.json_response({"error": "Кейс пуст"}, status=400)

        # 4. Рандом
        weights = [10000 / (item['price'] + 1) for item in items]
        dropped = [random.choices(items, weights=weights, k=1)[0] for _ in range(count)]
        
        await update_user_balance(user_id, -total_price) 
        await add_items_to_inventory_batch(user_id, dropped)
        
        return web.json_response({"dropped": dropped})
    except Exception as e: 
        logging.error(f"Error api_open_case: {e}")
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
        logging.error(f"Error api_sell_batch: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_upgrade(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        item_id = int(data.get('item_id'))
        target_id = int(data.get('target_id'))
        
        # 1. Ищем мой предмет (INV_KEYS)
        raw_inv = await get_inventory_grouped(user_id)
        # Преобразуем весь инвентарь в dict, чтобы найти нужное
        inventory = [to_dict(i, ['item_id', 'name', 'rarity', 'image_url', 'price', 'quantity']) for i in raw_inv]
        
        my_item = next((i for i in inventory if i['item_id'] == item_id and i['quantity'] > 0), None)
        
        if not my_item: 
            return web.json_response({"error": "Предмет не найден"}, status=400)
        
        # 2. Ищем цель (ITEM_KEYS)
        raw_all_items = await get_all_items_sorted()
        all_items = [to_dict(i, ITEM_KEYS) for i in raw_all_items]
        target_item = next((i for i in all_items if i['id'] == target_id), None)
        
        if not target_item:
            return web.json_response({"error": "Цель не найдена"}, status=400)

        # 3. Шанс
        chance = (my_item['price'] / target_item['price']) * 95
        if chance > 80: chance = 80
        if chance < 1: chance = 1

        # 4. Удаляем
        await delete_one_item_by_id(user_id, item_id)
        
        # 5. Крутим
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
        logging.error(f"Upgrade Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

app.add_routes([
    web.get('/', web_index), 
    web.post('/api/data', api_get_data), 
    web.post('/api/open', api_open_case), 
    web.post('/api/sell_batch', api_sell_batch), 
    web.post('/api/upgrade', api_upgrade), 
    web.static('/static', STATIC_DIR)
])