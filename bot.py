import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2
from database import get_user, get_inventory, get_leaderboard, get_all_cases, get_case_items, add_item_to_inventory, update_user_balance, get_case_data

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8292962840:AAEQ-0hJlKyX-NBHd9I9YlmxU17NRKwgOME" 
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app"
# Путь к папке static
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = web.Application()

# Подключаем шаблоны
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await get_user(message.from_user.id, message.from_user.username or "Anon")
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🍕 ИГРАТЬ (Web App)", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    
    await message.answer_photo(
        photo="https://i.imgur.com/6X7p3T8.png", # Можешь заменить на свою картинку
        caption=f"Йо, {message.from_user.first_name}! \nТут полный бреинрот. Открывай кейсы!",
        reply_markup=kb
    )

# --- API ---

async def web_index(request):
    return aiohttp_jinja2.render_template('index.html', request, {})

async def api_get_data(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        username = data.get('username')
        
        user_data = await get_user(user_id, username)
        
        user_dict = None
        if user_data:
            user_keys = ['id', 'tg_id', 'username', 'balance']
            user_dict = dict(zip(user_keys, user_data))
        
        return web.json_response({
            "user": user_dict, 
            "inventory": await get_inventory(user_id),
            "cases": await get_all_cases(),
            "case_items": await get_case_items(case_id=None), # Все предметы для рулетки
            "leaderboard": await get_leaderboard()
        })
    except Exception as e:
        logging.error(f"Error in api_get_data: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_open_case(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        case_id = int(data.get('case_id')) 
        
        case_data = await get_case_data(case_id)
        if not case_data:
            return web.json_response({"error": "Кейс не найден"}, status=404)
            
        case_price = case_data['price']
        user = await get_user(user_id, 'temp') 
        user_balance = user[3] 

        if user_balance < case_price:
             return web.json_response({"error": "Недостаточно средств!"}, status=400)

        items = await get_case_items(case_id) 
        if not items: 
            return web.json_response({"error": "Кейс пуст"}, status=400)

        # Логика дропа
        weights = [10000 / (item['price'] + 1) for item in items]
        dropped_item = random.choices(items, weights=weights, k=1)[0]
        
        await update_user_balance(user_id, -case_price) 
        await add_item_to_inventory(user_id, dropped_item)
        
        return web.json_response({"dropped": dropped_item})
    except Exception as e:
        logging.error(f"Error in api_open_case: {e}")
        return web.json_response({"error": str(e)}, status=500)

# Маршруты
app.add_routes([
    web.get('/', web_index),
    web.post('/api/data', api_get_data),
    web.post('/api/open', api_open_case),
    web.static('/static', STATIC_DIR) # Раздача стилей и скриптов
])