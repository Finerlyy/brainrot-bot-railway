import aiosqlite
import os

# Автоматический выбор пути к базе данных
if os.path.exists("/data"):
    # Путь для хостинга (Railway и т.д.)
    DB_NAME = "/data/brainrot.db"
else:
    # Путь для локального запуска
    DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица users
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            stars INTEGER DEFAULT 0,
            last_weekly_case TIMESTAMP
        )''')
        
        # Таблица inventory
        await db.execute('''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            rarity TEXT,
            price INTEGER,
            image_url TEXT
        )''')

        # Таблица items
        await db.execute('''CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rarity TEXT,
            price INTEGER,
            image_url TEXT
        )''')
        
        # Начальные предметы
        cursor = await db.execute("SELECT count(*) FROM items")
        count = await cursor.fetchone()
        if count[0] == 0:
            items = [
                ("Skibidi Carbonara", "Common", 10, "https://placehold.co/200x200/333/FFF?text=Skibidi+Carbonara"),
                ("Rizz Lasagna", "Uncommon", 50, "https://placehold.co/200x200/green/FFF?text=Rizz+Lasagna"),
                ("Sigma Spaghetti", "Rare", 150, "https://placehold.co/200x200/blue/FFF?text=Sigma+Spaghetti"),
            ]
            await db.executemany("INSERT INTO items (name, rarity, price, image_url) VALUES (?, ?, ?, ?)", items)
            await db.commit()
            print(f"База данных инициализирована в: {DB_NAME}")

# --- Функции для Основного Бота (API) ---

async def get_user(user_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_item_to_inventory(user_id, item):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO inventory (user_id, item_name, rarity, price, image_url) VALUES (?, ?, ?, ?, ?)",
                         (user_id, item['name'], item['rarity'], item['price'], item['image_url']))
        await db.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (item['price'], user_id))
        await db.commit()

async def get_all_items():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM items") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def get_inventory(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM inventory WHERE user_id = ? ORDER BY id DESC", (user_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT username, stars FROM users ORDER BY stars DESC LIMIT 10") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

# --- Функции для Админ Бота ---

async def admin_add_new_item(name, rarity, price, image_url):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO items (name, rarity, price, image_url) VALUES (?, ?, ?, ?)", 
                         (name, rarity, price, image_url))
        await db.commit()