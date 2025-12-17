import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2

# Импортируем функции БД
from database import (
    get_user, get_inventory_grouped, get_leaderboard, get_all_cases, 
    get_case_items, add_items_to_inventory_batch, update_user_balance, 
    get_case_data, sell_items_batch_db, get_all_items_sorted, 
    delete_one_item_by_id, add_item_to_inventory
)

# --- ВСТАВЬ СЮДА СВОЙ ТОКЕН ---
TOKEN = "8292962840:AAHqOus6QIKOhYoYeEXjE4zMGHkGRSR_Ztc" 
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app"
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = web.Application()

aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

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
        user_data = await get_user(user_id, data.get('username'))
        
        raw_inv = await get_inventory_grouped(user_id)
        inventory = []
        for item in raw_inv:
            p, r = item['price'], item['rarity']
            # Логика цен продажи
            sell = int(p*0.15) if r=='Common' else int(p*0.4) if r=='Uncommon' else int(p*1.1) if r=='Rare' else int(p*3.5)
            i_dict = dict(item)
            i_dict['sell_price'] = max(1, sell)
            inventory.append(i_dict)

        return web.json_response({
            "user": user_data, 
            "inventory": inventory, 
            "cases": await get_all_cases(), 
            "leaderboard": await get_leaderboard(),
            "all_items": await get_all_items_sorted()
        })
    except Exception as e: 
        logging.error(f"Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_open_case(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id')); case_id = int(data.get('case_id')); count = int(data.get('count', 1))
        
        case_data = await get_case_data(case_id)
        total_price = case_data['price'] * count
        user = await get_user(user_id, 'temp')

        if user['balance'] < total_price: return web.json_response({"error": "Мало денег!"}, status=400)

        items = await get_case_items(case_id)
        # Взвешенный рандом
        weights = [10000 / (item['price'] + 1) for item in items]
        dropped = [random.choices(items, weights=weights, k=1)[0] for _ in range(count)]
        
        await update_user_balance(user_id, -total_price) 
        await add_items_to_inventory_batch(user_id, dropped)
        return web.json_response({"dropped": dropped})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def api_sell_batch(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        item_id = int(data.get('item_id')) 
        count = int(data.get('count'))
        price_per_item = int(data.get('price_per_item'))
        
        total_price = count * price_per_item
        
        success = await sell_items_batch_db(user_id, item_id, count, total_price)
        return web.json_response({"status": "ok"}) if success else web.json_response({"error": "Ошибка продажи"}, status=400)
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def api_upgrade(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        item_id = int(data.get('item_id')) # ID предмета, который отдаем
        target_id = int(data.get('target_id'))
        
        # 1. Проверяем наличие
        raw_inv = await get_inventory_grouped(user_id)
        my_item = next((i for i in raw_inv if i['item_id'] == item_id and i['quantity'] > 0), None)
        if not my_item: return web.json_response({"error": "Предмет не найден или кончился"}, status=400)
        
        all_items = await get_all_items_sorted()
        target_item = next((i for i in all_items if i['id'] == target_id), None)
        
        # 2. Считаем шанс
        chance = (my_item['price'] / target_item['price']) * 95
        if chance > 80: chance = 80
        if chance < 1: chance = 1

        # 3. УДАЛЯЕМ ПРЕДМЕТ СРАЗУ (Сжигаем)
        await delete_one_item_by_id(user_id, item_id)
        
        # 4. Крутим рулетку
        roll = random.uniform(0, 100)
        is_win = roll <= chance
        
        item_data = None
        if is_win:
            await add_item_to_inventory(user_id, target_item)
            item_data = target_item
        
        # Лог для отладки
        print(f"Upgrade User={user_id}: Chance={chance:.2f}, Roll={roll:.2f}, Win={is_win}")

        return web.json_response({
            "status": "win" if is_win else "lose", 
            "item": item_data,
            "roll": roll,
            "chance": chance
        })
    except Exception as e: 
        print(f"Upgrade Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

app.add_routes([
    web.get('/', web_index), 
    web.post('/api/data', api_get_data), 
    web.post('/api/open', api_open_case), 
    web.post('/api/sell_batch', api_sell_batch), 
    web.post('/api/upgrade', api_upgrade), 
    web.static('/static', STATIC_DIR)
])