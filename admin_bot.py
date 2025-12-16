import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from database import update_user_balance, admin_get_all_users

# НОВЫЙ ТОКЕН АДМИНА:
TOKEN = "8547237995:AAHrUOQInO5b9HVLGbb_2eIlWKIdhzVo86Y"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👨‍💻 <b>Админ-панель Brainrot Drop</b>\n\nКоманды:\n/give [id] [сумма] - Выдать баланс\n/users - Список игроков", parse_mode="HTML")

@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    users = await admin_get_all_users()
    text = "👥 <b>Игроки:</b>\n"
    for u in users:
        text += f"ID: {u['tg_id']} | {u['username']} | 💰 {u['balance']}\n"
    await message.answer(text[:4000], parse_mode="HTML")

@dp.message(Command("give"))
async def cmd_give(message: types.Message):
    try:
        args = message.text.split()
        if len(args) != 3:
            return await message.answer("Ошибка! Пиши так: `/give 12345678 1000`")
        
        user_id = int(args[1])
        amount = int(args[2])
        
        await update_user_balance(user_id, amount)
        await message.answer(f"✅ Выдано {amount} звезд пользователю {user_id}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")