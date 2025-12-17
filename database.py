import aiosqlite
import sqlite3
import logging

DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row 
        # Создаем таблицы (в users добавлено поле ip)
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 5000, ip TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER, icon_url TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, rarity TEXT, price INTEGER, image_url TEXT, sound_url TEXT, case_id INTEGER, FOREIGN KEY (case_id) REFERENCES cases(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, item_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES items(id))")
        
        # --- МИГРАЦИЯ (Если база старая, добавляем колонку ip) ---
        try:
            await db.execute("ALTER TABLE users ADD COLUMN ip TEXT")
        except:
            pass # Колонка уже есть, игнорируем ошибку

        await db.commit()
        
        # --- НАПОЛНЕНИЕ БАЗЫ ---
        case_name = '🧠 Ultimate Brainrot Case'
        case_price = 300
        case_icon = 'https://i.ibb.co/mCZ9d327/1000002237.jpg'

        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (case_name, case_price, case_icon))
        await db.execute("UPDATE cases SET icon_url = ? WHERE name = ?", (case_icon, case_name))
        await db.commit()

        async with db.execute("SELECT id FROM cases WHERE name = ?", (case_name,)) as cur:
            row = await cur.fetchone()
            case_id = row[0] if row else None

        if case_id:
            items_data = [
                ('Lirili Bat Guy', 'Common', 100, 'https://i.imgur.com/vZkT4cu.jpeg', '-', case_id),
                ('Tung Tung Elephant', 'Common', 150, 'https://i.imgur.com/4RtWcWY.jpeg', '-', case_id),
                ('Tatata Teapot', 'Uncommon', 400, 'https://i.imgur.com/DZDL8RI.jpeg', '-', case_id),
                ('Tralala Shark', 'Rare', 1200, 'https://i.imgur.com/iDcJaMp.jpeg', '-', case_id),
                ('Orcalero Orca', 'Mythical', 3500, 'https://i.imgur.com/EsqyjjW.jpeg', '-', case_id),
                ('Chimpanzini Bananini', 'Mythical', 10000, 'https://i.imgur.com/0QTbLT8.jpeg', '-', case_id),
            ]
            for i in items_data:
                async with db.execute("SELECT id FROM items WHERE name = ?", (i[0],)) as cur:
                    if not await cur.fetchone():
                        await db.execute("INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", i)
        await db.commit()

# --- ФУНКЦИИ ---

async def get_user(tg_id, username):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            user = await cursor.fetchone()
        
        if user is None:
            try:
                await db.execute("INSERT INTO users (tg_id, username) VALUES (?, ?)", (tg_id, username))
                await db.commit()
            except sqlite3.IntegrityError: pass
            async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
                user = await cursor.fetchone()
        return user

# НОВАЯ ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ IP
async def update_user_ip(tg_id, ip_address):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ip = ? WHERE tg_id = ?", (ip_address, tg_id))
        await db.commit()

async def update_user_balance(tg_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (amount, tg_id))
        await db.commit()

async def get_all_cases():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases") as cursor: 
            return await cursor.fetchall()

async def get_case_data(case_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)) as cursor:
            return await cursor.fetchone()

async def get_case_items(case_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql = "SELECT * FROM items" if case_id is None else "SELECT * FROM items WHERE case_id = ?"
        params = () if case_id is None else (case_id,)
        async with db.execute(sql, params) as cursor: 
            return await cursor.fetchall()

async def get_all_items_sorted():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM items ORDER BY price ASC") as cursor:
            return await cursor.fetchall()

async def add_items_to_inventory_batch(tg_user_id, items_list):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user_row = await cursor.fetchone()
            if not user_row: return 
            user_pk_id = user_row[0] 
            
        insert_data = []
        for item in items_list:
            i_id = item.get('id') if isinstance(item, dict) else item[0]
            insert_data.append((user_pk_id, i_id))

        await db.executemany("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", insert_data)
        await db.commit()

async def add_item_to_inventory(tg_user_id, item):
    await add_items_to_inventory_batch(tg_user_id, [item])

async def get_inventory_grouped(user_id_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (user_id_tg,)) as cursor:
            u = await cursor.fetchone()
            if not u: return []
            user_pk = u[0]

        sql = """
            SELECT i.id as item_id, i.name, i.rarity, i.image_url, i.price, COUNT(inv.item_id) as quantity
            FROM inventory AS inv 
            JOIN items AS i ON inv.item_id = i.id 
            WHERE inv.user_id = ?
            GROUP BY i.id, i.name, i.rarity, i.image_url, i.price
        """
        async with db.execute(sql, (user_pk,)) as cursor:
            return await cursor.fetchall()

async def sell_items_batch_db(tg_user_id, item_id, count, total_price):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u[0]

        sql = """
            DELETE FROM inventory 
            WHERE rowid IN (
                SELECT rowid FROM inventory 
                WHERE user_id = ? AND item_id = ? 
                LIMIT ?
            )
        """
        await db.execute(sql, (user_pk, item_id, count))
        
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (total_price, tg_user_id))
        await db.commit()
        return True

async def delete_one_item_by_id(tg_user_id, item_id):
    return await sell_items_batch_db(tg_user_id, item_id, 1, 0)

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT username, balance FROM users WHERE tg_id != 0 ORDER BY balance DESC LIMIT 10") as cursor:
            return [dict(row) if hasattr(row, 'keys') else {'username': row[0], 'balance': row[1]} for row in await cursor.fetchall()]

async def admin_get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM users WHERE tg_id != 0") as cursor:
            return await cursor.fetchall()