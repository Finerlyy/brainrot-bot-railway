import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2
# Импортируем НОВЫЕ функции БД
from database import get_user, get_inventory, get_leaderboard, get_all_cases, get_case_items, add_item_to_inventory, update_user_balance, get_case_data

# --- ТВОИ ДАННЫЕ И КОНФИГУРАЦИЯ ---
# ИСПРАВЛЕНИЕ: Токен взят в кавычки!
TOKEN = "8292962840:AAGp3Zz6xb5bMd-5E4wUhXZqWWJ6Mrv1GRU" 
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app" 
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static') # <--- ПУТЬ К ПАПКЕ STATIC

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = web.Application()

# Подключаем шаблоны (папка templates)
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # При первом запуске создаст пользователя или получит существующего
    await get_user(message.from_user.id, message.from_user.username or "MemeLover")
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🍕 ИГРАТЬ (Web App)", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    
    # 🛑 ВАЖНО: ЗАМЕНИ ССЫЛКУ НИЖЕ НА РЕАЛЬНУЮ ПРЯМУЮ ССЫЛКУ НА ИЗОБРАЖЕНИЕ
    await message.answer_photo(
        photo="https://i.imgur.com/example_of_valid_image.png", # <--- ЗАМЕНИ ЭТУ ССЫЛКУ!
        caption=f"Йо, {message.from_user.first_name}! \nТут итальянский бреинрот. Жми кнопку, чтобы открыть кейсы.",
        reply_markup=kb
    )

# --- WEB APP API ---

async def web_index(request):
    return aiohttp_jinja2.render_template('index.html', request, {})

async def api_get_data(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    username = data.get('username')
    
    user_data = await get_user(user_id, username)
    
    # Явное преобразование кортежа (tuple) в словарь (dict)
    user_dict = None
    if user_data:
        # Предполагаем порядок столбцов: id, tg_id, username, balance
        user_keys = ['id', 'tg_id', 'username', 'balance']
        user_dict = dict(zip(user_keys, user_data))
    
    return web.json_response({
        "user": user_dict, 
        "inventory": await get_inventory(user_id),
        "cases": await get_all_cases(),
        "case_items": await get_case_items(case_id=None),
        "leaderboard": await get_leaderboard()
    })

async def api_open_case(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    case_id = int(data.get('case_id')) 
    
    case_data = await get_case_data(case_id)
    if not case_data:
        return web.json_response({"error": "Case not found"}, status=404)
        
    case_price = case_data['price']
    user = await get_user(user_id, 'temp') # Получаем текущий баланс
    user_balance = user[3] # Balance находится в 4-м элементе кортежа

    if user_balance < case_price:
         return web.json_response({"error": "Insufficient balance"}, status=400)

    items = await get_case_items(case_id) 
    
    if not items: return web.json_response({"error": "No items in this case"}, status=400)

    # Логика рандома: чем дороже, тем меньше вероятность
    weights = [10000 / (item['price'] + 1) for item in items]
    dropped_item = random.choices(items, weights=weights, k=1)[0]
    
    # Списываем баланс и добавляем предмет
    await update_user_balance(user_id, -case_price) 
    await add_item_to_inventory(user_id, dropped_item)
    
    return web.json_response({"dropped": dropped_item})

# Настраиваем маршруты (routes)
app.add_routes([
    web.get('/', web_index),
    web.post('/api/data', api_get_data),
    web.post('/api/open', api_open_case),
    web.static('/static', STATIC_DIR) # <--- ДОБАВЛЕН МАРШРУТ ДЛЯ СТАТИКИ
])