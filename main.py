import asyncio
import logging
import os
import sys

from aiohttp import web
from database import init_db

# Импортируем оба бота
from bot import bot as game_bot, dp as game_dp, app
from admin_bot import bot as admin_bot, dp as admin_dp

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def on_startup(app):
    """Запуск"""
    logging.info("🛠 Инициализация базы данных...")
    await init_db()
    
    logging.info("🚀 Запуск обоих ботов...")
    asyncio.create_task(game_dp.start_polling(game_bot))
    asyncio.create_task(admin_dp.start_polling(admin_bot))

async def on_shutdown(app):
    """Остановка"""
    await game_dp.stop_polling()
    await admin_dp.stop_polling()

if __name__ == "__main__":
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"🌍 Web Server running on port {port}")
    
    web.run_app(app, port=port)