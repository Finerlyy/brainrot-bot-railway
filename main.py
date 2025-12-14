import asyncio
import logging
import os
from aiohttp import web
from database import init_db

# Импортируем модули ботов
from bot import bot as game_bot, dp as game_dp, app as game_app
from admin_bot import bot as admin_bot, dp as admin_dp

logging.basicConfig(level=logging.INFO)

async def start_web_server():
    # Читаем порт из переменной окружения Railway (по умолчанию 8080)
    PORT = int(os.environ.get("PORT", 8080)) 
    
    runner = web.AppRunner(game_app)
    await runner.setup()
    # Запуск на порту 0.0.0.0
    site = web.TCPSite(runner, '0.0.0.0', PORT) 
    await site.start()
    print(f"🌍 Web Server running on port {PORT}")

async def main():
    # 1. Инициализируем базу данных (путь /data/brainrot.db для сохранения данных)
    await init_db()

    # 2. Запускаем веб-сервер сайта
    await start_web_server()

    # 3. Запускаем основного бота и админ-бота параллельно
    print("🚀 Both bots starting polling...")
    await asyncio.gather(
        game_dp.start_polling(game_bot),
        admin_dp.start_polling(admin_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())