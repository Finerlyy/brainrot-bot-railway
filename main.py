import asyncio
import logging
from aiohttp import web
from bot import bot as main_bot, dp as main_dp, app
from admin_bot import bot as admin_bot, dp as admin_dp
from database import init_db

async def main():
    await init_db()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌍 Web server started on port 8080")

    await main_bot.delete_webhook(drop_pending_updates=True)
    await admin_bot.delete_webhook(drop_pending_updates=True)

    await asyncio.gather(
        main_dp.start_polling(main_bot),
        admin_dp.start_polling(admin_bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass