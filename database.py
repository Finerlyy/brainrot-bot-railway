import aiosqlite
import sqlite3

DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row 
        
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 500)")
        await db.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER, icon_url TEXT)")
        # Добавляем поле sell_price в items, если его нет (для баланса)
        # Но для простоты будем рассчитывать цену продажи динамически в коде
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, rarity TEXT, price INTEGER, image_url TEXT, sound_url TEXT, case_id INTEGER, FOREIGN KEY (case_id) REFERENCES cases(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, user_id INTEGER, item_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES items(id))")
        
        await db.commit()
        
        # Данные по умолчанию
        await db.execute("INSERT OR IGNORE INTO users (tg_id, username, balance) VALUES (?, ?, ?)", (0, 'system', 0))
        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", ('🗿 Base Case', 100, 'https://cdn-icons-png.flaticon.com/512/9334/9334614.png'))
        await db.commit()

# --- ОСНОВНЫЕ ФУНКЦИИ ---

async def get_user(tg_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            user = await cursor.fetchone()
        
        if user is None:
            try:
                await db.execute("INSERT INTO users (tg_id, username) VALUES (?, ?)", (tg_id, username))
                await db.commit()
            except sqlite3.IntegrityError:
                pass
            async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
                user = await cursor.fetchone()
        return user

async def update_user_balance(tg_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
        await db.commit()

async def get_all_cases():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def get_case_data(case_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)) as cursor:
            res = await cursor.fetchone()
            return dict(res) if res else None

async def get_case_items(case_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql = "SELECT * FROM items" if case_id is None else "SELECT * FROM items WHERE case_id = ?"
        params = () if case_id is None else (case_id,)
        async with db.execute(sql, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def add_item_to_inventory(user_id, item):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (user_id, item['id']))
        await db.commit()

async def get_inventory(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        # Получаем также ID записи в инвентаре (inv_id), чтобы удалять конкретный предмет
        sql = "SELECT inv.id as inv_id, i.id as item_id, i.name, i.rarity, i.image_url, i.price FROM inventory AS inv JOIN items AS i ON inv.item_id = i.id WHERE inv.user_id = ?"
        async with db.execute(sql, (user_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

# НОВАЯ ФУНКЦИЯ: Продажа предмета
async def sell_item_db(user_id, inv_id, price):
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Удаляем из инвентаря
        await db.execute("DELETE FROM inventory WHERE id = ? AND user_id = ?", (inv_id, user_id))
        # 2. Начисляем баланс
        await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (price, user_id))
        await db.commit()

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT username, balance FROM users WHERE tg_id != 0 ORDER BY balance DESC LIMIT 10") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

# --- ФУНКЦИИ АДМИНА ---

async def admin_get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM users WHERE tg_id != 0") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def admin_add_new_item(item):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", 
                         (item['name'], item['rarity'], item['price'], item['image_url'], item['sound_url'], item['case_id']))
        await db.commit()

# НОВАЯ: Обновление предмета
async def admin_update_item_field(item_id, field, value):
    async with aiosqlite.connect(DB_NAME) as db:
        # Внимание: прямая вставка field небезопасна в production, но для админ-бота пойдет
        query = f"UPDATE items SET {field} = ? WHERE id = ?"
        await db.execute(query, (value, item_id))
        await db.commit()