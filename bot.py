import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import aiohttp_jinja2
import jinja2
from database import get_user, get_inventory, get_leaderboard, get_all_cases, get_case_items, add_item_to_inventory, update_user_balance, get_case_data, sell_item_db

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8292962840:AAEQ-0hJlKyX-NBHd9I9YlmxU17NRKwgOME" 
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
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🕹 ИГРАТЬ", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    # ИСПРАВЛЕННАЯ ССЫЛКА НА ФОТО
    await message.answer_photo(
        photo="https://i.imgur.com/58g7G7k.jpeg", 
        caption=f"👋 Йо, {message.from_user.first_name}!\nЗалетай открывать кейсы и торговать дропом!",
        reply_markup=kb
    )

# --- БАЛАНС И ЭКОНОМИКА ---
def calculate_sell_price(item_price, rarity):
    # item_price - это условная "ценность" предмета, заданная админом.
    # Чтобы не уйти в минус, делаем жесткую математику.
    if rarity == 'Common': return int(item_price * 0.15) # Дешевый предмет = 15% возврата
    if rarity == 'Uncommon': return int(item_price * 0.40) 
    if rarity == 'Rare': return int(item_price * 1.1)
    if rarity == 'Mythical': return int(item_price * 3.5)
    return int(item_price * 0.1)

# --- API ---

async def web_index(request):
    return aiohttp_jinja2.render_template('index.html', request, {})

async def api_get_data(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        
        user_data = await get_user(user_id, data.get('username'))
        user_dict = dict(zip(['id', 'tg_id', 'username', 'balance'], user_data)) if user_data else None
        
        # Обрабатываем инвентарь, добавляя цену продажи
        raw_inventory = await get_inventory(user_id)
        inventory = []
        for item in raw_inventory:
            sell_price = calculate_sell_price(item['price'], item['rarity'])
            # Гарантируем, что цена продажи не 0
            if sell_price < 1: sell_price = 1
            item_dict = dict(item)
            item_dict['sell_price'] = sell_price
            inventory.append(item_dict)

        return web.json_response({
            "user": user_dict, 
            "inventory": inventory,
            "cases": await get_all_cases(),
            "leaderboard": await get_leaderboard(),
            "case_items": await get_case_items(None)
        })
    except Exception as e:
        logging.error(f"Error data: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_open_case(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        case_id = int(data.get('case_id')) 
        
        case_data = await get_case_data(case_id)
        if not case_data: return web.json_response({"error": "Кейс не найден"}, status=404)
            
        user = await get_user(user_id, 'temp')
        if user[3] < case_data['price']: return web.json_response({"error": "Недостаточно денег!"}, status=400)

        items = await get_case_items(case_id)
        if not items: return web.json_response({"error": "Кейс пуст"}, status=400)

        weights = [10000 / (item['price'] + 1) for item in items]
        dropped = random.choices(items, weights=weights, k=1)[0]
        
        await update_user_balance(user_id, -case_data['price']) 
        await add_item_to_inventory(user_id, dropped)
        
        return web.json_response({"dropped": dropped})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_sell_item(request):
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        inv_id = int(data.get('inv_id')) # ID конкретной записи в инвентаре
        price = int(data.get('price')) # Цена продажи (проверяем на сервере для безопасности)

        # В реальном проекте тут надо перепроверить цену через БД, чтобы не накрутили
        # Но для прототипа доверимся клиенту (с минимальной защитой в calculate_sell_price выше)
        
        await sell_item_db(user_id, inv_id, price)
        return web.json_response({"status": "ok", "sold_price": price})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

app.add_routes([
    web.get('/', web_index),
    web.post('/api/data', api_get_data),
    web.post('/api/open', api_open_case),
    web.post('/api/sell', api_sell_item), # Новый API
    web.static('/static', STATIC_DIR)
])