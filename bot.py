import logging
import random
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2

# Импортируем функции базы данных
from database import get_user, get_inventory, get_leaderboard, get_all_cases, get_case_items, add_items_to_inventory_batch, update_user_balance, get_case_data, sell_item_db

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8292962840:AAEQ-0hJlKyX-NBHd9I9YlmxU17NRKwgOME"
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app"
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = web.Application()

# Настройка шаблонов
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

# --- ОБРАБОТЧИКИ TELEGRAM ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Регистрируем юзера при старте
    await get_user(message.from_user.id, message.from_user.username or "Anon")
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🕹 ОТКРЫТЬ КЕЙСЫ 🎰", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    
    await message.answer_photo(
        photo="https://i.imgur.com/UOAnvOc.png", 
        caption=f"Йо, {message.from_user.first_name}! 🗿\nЗалетай в Brainrot Drop! Тут самые редкие мемы.", 
        reply_markup=kb
    )

# --- WEB API (БЭКЕНД ИГРЫ) ---

async def web_index(request):
    # ver=random... нужен чтобы сбрасывать кэш стилей/скриптов
    return aiohttp_jinja2.render_template('index.html', request, {'ver': random.randint(1, 9999)})

async def api_get_data(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        
        user_data = await get_user(user_id, data.get('username'))
        user_dict = dict(zip(['id', 'tg_id', 'username', 'balance'], user_data)) if user_data else None
        
        raw_inv = await get_inventory(user_id)
        inventory = []
        for item in raw_inv:
            p, r = item['price'], item['rarity']
            # Динамическая цена продажи
            sell = int(p*0.15) if r=='Common' else int(p*0.4) if r=='Uncommon' else int(p*1.1) if r=='Rare' else int(p*3.5)
            i_dict = dict(item)
            i_dict['sell_price'] = max(1, sell)
            inventory.append(i_dict)
            
        return web.json_response({
            "user": user_dict, 
            "inventory": inventory, 
            "cases": await get_all_cases(), 
            "leaderboard": await get_leaderboard(), 
            "case_items": await get_case_items(None)
        })
    except Exception as e: 
        return web.json_response({"error": str(e)}, status=500)

async def api_open_case(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        case_id = int(data.get('case_id'))
        count = int(data.get('count', 1))

        if count < 1 or count > 10:
             return web.json_response({"error": "Максимум 10 за раз!"}, status=400)
        
        case_data = await get_case_data(case_id)
        if not case_data: return web.json_response({"error": "Кейс не найден"}, status=404)
            
        total_price = case_data['price'] * count
        user = await get_user(user_id, 'temp')
        
        if user['balance'] < total_price: 
            return web.json_response({"error": f"Не хватает денег! Нужно {total_price} 💰"}, status=400)

        items = await get_case_items(case_id)
        if not items: return web.json_response({"error": "Кейс пуст"}, status=400)

        # Логика выпадения с учетом веса (цены)
        weights = [10000 / (item['price'] + 1) for item in items]
        
        dropped_items = []
        for _ in range(count):
            dropped_items.append(random.choices(items, weights=weights, k=1)[0])
        
        # Списываем баланс и выдаем предметы
        await update_user_balance(user_id, -total_price) 
        await add_items_to_inventory_batch(user_id, dropped_items)
        
        return web.json_response({"dropped": dropped_items, "total_spent": total_price})
    except Exception as e:
        logging.error(f"Open error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_sell_item(request):
    try:
        data = await request.json()
        user_id_tg = int(data.get('user_id'))
        inv_id = int(data.get('inv_id'))
        price = int(data.get('price'))
        
        success = await sell_item_db(user_id_tg, inv_id, price)
        if success:
            return web.json_response({"status": "ok"})
        else:
            return web.json_response({"error": "Ошибка продажи"}, status=400)
    except Exception as e:
        logging.error(f"Sell error: {e}")
        return web.json_response({"error": str(e)}, status=500)

app.add_routes([
    web.get('/', web_index),
    web.post('/api/data', api_get_data),
    web.post('/api/open', api_open_case),
    web.post('/api/sell', api_sell_item),
    web.static('/static', STATIC_DIR)
])