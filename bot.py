import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2
from database import get_user, get_all_items, add_item_to_inventory, get_inventory, get_leaderboard

# --- ТВОИ ДАННЫЕ И КОНФИГУРАЦИЯ ---
# ЗАМЕНЕННЫЙ ТОКЕН: 8292962840:AAGp3Zz6xb5bMd-5E4wUhXZqWWJ6Mrv1GRU
TOKEN = "8292962840:AAGp3Zz6xb5bMd-5E4wUhXZqWWJ6Mrv1GRU" 
WEB_APP_URL = "https://brainrot-bot-railway-production.up.railway.app/" # <--- ССЫЛКА БУДЕТ ЗДЕСЬ

logging.basicConfig(level=logging.INFO)
bot = Bot(token=8292962840:AAGp3Zz6xb5bMd-5E4wUhXZqWWJ6Mrv1GRU)
dp = Dispatcher()
app = web.Application()

# Подключаем шаблоны (папка templates)
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await get_user(message.from_user.id, message.from_user.username or "MemeLover")
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🍕 ИГРАТЬ (Web App)", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer_photo(
        photo="https://placehold.co/600x400/121212/00ff88?text=BRAINROT+CASES",
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
    user = await get_user(user_id, username)
    return web.json_response({
        "user": dict(user) if user else None,
        "inventory": await get_inventory(user_id),
        "case_items": await get_all_items(),
        "leaderboard": await get_leaderboard()
    })

async def api_open_case(request):
    data = await request.json()
    user_id = int(data.get('user_id'))
    items = await get_all_items()
    
    if not items: return web.json_response({"error": "No items in case"}, status=400)

    # Логика рандома: чем дороже, тем меньше вероятность
    weights = [10000 / (item['price'] + 1) for item in items]
    dropped_item = random.choices(items, weights=weights, k=1)[0]
    
    await add_item_to_inventory(user_id, dropped_item)
    return web.json_response({"dropped": dropped_item})

# Настраиваем маршруты (routes)
app.add_routes([
    web.get('/', web_index),
    web.post('/api/data', api_get_data),
    web.post('/api/open', api_open_case),
])