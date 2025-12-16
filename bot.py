import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2

# Импортируем обновленные функции
from database import (
    get_user, get_inventory, get_leaderboard, get_all_cases, 
    get_case_items, add_items_to_inventory_batch, update_user_balance, 
    get_case_data, sell_item_db, get_all_items_sorted, 
    delete_item_from_inventory, add_item_to_inventory
)

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8292962840:AAHqOus6QIKOhYoYeEXjE4zMGHkGRSR_Ztc" # Ваш токен
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
        
        # Инвентарь
        raw_inv = await get_inventory(user_id)
        inventory = []
        for item in raw_inv:
            p, r = item['price'], item['rarity']
            sell = int(p*0.15) if r=='Common' else int(p*0.4) if r=='Uncommon' else int(p*1.1) if r=='Rare' else int(p*3.5)
            i_dict = dict(item); i_dict['sell_price'] = max(1, sell)
            inventory.append(i_dict)

        return web.json_response({
            "user": user_data, 
            "inventory": inventory, 
            "cases": await get_all_cases(), 
            "leaderboard": await get_leaderboard(),
            "all_items": await get_all_items_sorted() # ВАЖНО для правой части апгрейда
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
        weights = [10000 / (item['price'] + 1) for item in items]
        dropped = [random.choices(items, weights=weights, k=1)[0] for _ in range(count)]
        
        await update_user_balance(user_id, -total_price) 
        await add_items_to_inventory_batch(user_id, dropped)
        return web.json_response({"dropped": dropped})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def api_sell_item(request):
    try:
        data = await request.json()
        await sell_item_db(int(data.get('user_id')), int(data.get('inv_id')), int(data.get('price')))
        return web.json_response({"status": "ok"})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

async def api_upgrade(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id')); inv_id = int(data.get('inv_id')); target_id = int(data.get('target_id'))
        
        raw_inv = await get_inventory(user_id)
        my_item = next((i for i in raw_inv if i['inv_id'] == inv_id), None)
        if not my_item: return web.json_response({"error": "Предмет не найден"}, status=400)
        
        all_items = await get_all_items_sorted()
        target_item = next((i for i in all_items if i['id'] == target_id), None)
        
        chance = min(80, max(1, (my_item['price'] / target_item['price']) * 95))
        is_win = random.uniform(0, 100) <= chance
        
        await delete_item_from_inventory(user_id, inv_id)
        if is_win:
            await add_item_to_inventory(user_id, target_item)
            return web.json_response({"status": "win", "item": target_item})
        return web.json_response({"status": "lose"})
    except Exception as e: return web.json_response({"error": str(e)}, status=500)

app.add_routes([web.get('/', web_index), web.post('/api/data', api_get_data), web.post('/api/open', api_open_case), web.post('/api/sell', api_sell_item), web.post('/api/upgrade', api_upgrade), web.static('/static', STATIC_DIR)])