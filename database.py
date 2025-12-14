import aiosqlite
import sqlite3

DB_NAME = "brainrot.db"

# Асинхронная функция для инициализации БД
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Устанавливаем row_factory для удобства работы с результатами
        db.row_factory = sqlite3.Row 
        
        # Таблица пользователей (users)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                username TEXT,
                balance INTEGER DEFAULT 100
            )
        """)
        
        # Таблица кейсов (cases)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                price INTEGER,
                icon_url TEXT
            )
        """)
        
        # Таблица предметов (items) - СВЯЗАННА С case_id и sound_url
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                name TEXT,
                rarity TEXT,
                price INTEGER,
                image_url TEXT,
                sound_url TEXT,
                case_id INTEGER,
                FOREIGN KEY (case_id) REFERENCES cases(id)
            )
        """)

        # Таблица инвентаря (inventory)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                item_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (item_id) REFERENCES items(id)
            )
        """)
        
        await db.commit()
        
        # Заполнение начальными данными
        await db.execute("INSERT OR IGNORE INTO users (tg_id, username, balance) VALUES (?, ?, ?)", (0, 'system_user', 0))
        
        # 1. Добавляем начальный кейс (Цена 100)
        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", 
                         ('🗿 Brainrot Base Case', 100, 'https://i.imgur.com/base_icon.png'))
        
        # 2. Добавляем второй кейс (Цена 500)
        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", 
                         ('🌌 Meme Explorer Case', 500, 'https://i.imgur.com/explorer_icon.png'))
                         
        await db.commit()
        
        # Получаем ID кейсов
        base_case_id_row = await db.execute_fetchone("SELECT id FROM cases WHERE name = '🗿 Brainrot Base Case'")
        explorer_case_id_row = await db.execute_fetchone("SELECT id FROM cases WHERE name = '🌌 Meme Explorer Case'")
        
        base_case_id = base_case_id_row[0] if base_case_id_row else None
        explorer_case_id = explorer_case_id_row[0] if explorer_case_id_row else None
        
        # 3. Вставляем примеры предметов (только если кейсы найдены)
        if base_case_id:
            await db.execute("INSERT OR IGNORE INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", 
                             ('Тралалеро Тралала', 'Common', 50, 'https://i.imgur.com/tralalero_img.png', 'https://i.imgur.com/tralalero_sound.mp3', base_case_id))
            await db.execute("INSERT OR IGNORE INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", 
                             ('Тунг Тунг Тунг Сахуром', 'Uncommon', 150, 'https://i.imgur.com/sahroom_img.png', 'https://i.imgur.com/sahroom_sound.mp3', base_case_id))
        
        if explorer_case_id:
            await db.execute("INSERT OR IGNORE INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", 
                             ('Bazinga!', 'Rare', 800, 'https://i.imgur.com/bazinga_img.png', 'https://i.imgur.com/bazinga_sound.mp3', explorer_case_id))
            await db.execute("INSERT OR IGNORE INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", 
                             ('Skitibi Dop', 'Mythical', 5000, 'https://i.imgur.com/skitibi_img.png', 'https://i.imgur.com/skitibi_sound.mp3', explorer_case_id))
                             
        await db.commit()


# --- Вспомогательные функции ---

# Важно: get_user возвращает кортеж (tuple) для обратной совместимости с bot.py
async def get_user(tg_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute_fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        if user is None:
            await db.execute("INSERT INTO users (tg_id, username) VALUES (?, ?)", (tg_id, username))
            await db.commit()
            user = await db.execute_fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
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
        return await db.execute_fetchone("SELECT * FROM cases WHERE id = ?", (case_id,))

# Если case_id = None, возвращаем ВСЕ предметы (для генерации рулетки)
async def get_case_items(case_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        if case_id is None:
            sql = "SELECT * FROM items"
            params = ()
        else:
            sql = "SELECT * FROM items WHERE case_id = ?"
            params = (case_id,)
            
        async with db.execute(sql, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def add_item_to_inventory(user_id, item):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", 
                         (user_id, item['id']))
        await db.commit()

async def get_inventory(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql = """
            SELECT i.name, i.rarity, i.image_url 
            FROM inventory AS inv
            JOIN items AS i ON inv.item_id = i.id
            WHERE inv.user_id = ?
        """
        async with db.execute(sql, (user_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql = "SELECT username, balance FROM users WHERE tg_id != 0 ORDER BY balance DESC LIMIT 10"
        async with db.execute(sql) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

# --- Функции для Админ-бота ---
async def admin_add_new_item(item):
    """Добавляет новый предмет в базу данных."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item['name'], item['rarity'], item['price'], item['image_url'], item['sound_url'], item['case_id']))
        await db.commit()