import asyncio
import logging
import os
import sys

from aiohttp import web
from database import init_db

# Импортируем объекты ботов и приложения из bot.py и admin_bot.py
from bot import bot as game_bot, dp as game_dp, app
from admin_bot import bot as admin_bot, dp as admin_dp

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def on_startup(app):
    """Эта функция запустится вместе со стартом сайта"""
    logging.info("🛠 Инициализация базы данных...")
    await init_db()
    
    logging.info("🚀 Запуск поллинга ботов...")
    # Запускаем ботов в фоновом режиме (background tasks)
    asyncio.create_task(game_dp.start_polling(game_bot))
    asyncio.create_task(admin_dp.start_polling(admin_bot))

if __name__ == "__main__":
    # Добавляем задачу запуска в список aiohttp
    app.on_startup.append(on_startup)
    
    # Получаем порт от Railway (обязательно!)
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"🌍 Web Server running on port {port}")
    
    # Запускаем веб-сервер. Он же будет крутить цикл событий для ботов.
    web.run_app(app, port=port)