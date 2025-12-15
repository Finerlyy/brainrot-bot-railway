import aiosqlite
import sqlite3

DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row 
        
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 5000)")
        await db.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER, icon_url TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, rarity TEXT, price INTEGER, image_url TEXT, sound_url TEXT, case_id INTEGER, FOREIGN KEY (case_id) REFERENCES cases(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, user_id INTEGER, item_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES items(id))")
        
        await db.commit()
        
        # --- НАПОЛНЕНИЕ КОНТЕНТОМ (Ваш кейс) ---
        case_name = '🧠 Ultimate Brainrot Case'
        case_price = 300
        case_icon = 'https://i.imgur.com/UOAnvOc.png' 

        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (case_name, case_price, case_icon))
        await db.commit()

        async with db.execute("SELECT id FROM cases WHERE name = ?", (case_name,)) as cur:
            row = await cur.fetchone()
            case_id = row['id'] if row else None

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

# --- ФУНКЦИИ ПОЛЬЗОВАТЕЛЯ ---

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
        
        return dict(user) if user else None

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

async def add_items_to_inventory_batch(tg_user_id, items_list):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user_row = await cursor.fetchone()
            user_pk_id = user_row[0]

        insert_data = [(user_pk_id, item['id']) for item in items_list]
        await db.executemany("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", insert_data)
        await db.commit()

async def get_inventory(user_id_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (user_id_tg,)) as cursor:
            u = await cursor.fetchone()
            if not u: return []
            user_pk = u['id']

        sql = "SELECT inv.id as inv_id, i.id as item_id, i.name, i.rarity, i.image_url, i.price FROM inventory AS inv JOIN items AS i ON inv.item_id = i.id WHERE inv.user_id = ?"
        async with db.execute(sql, (user_pk,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def sell_item_db(tg_user_id, inv_id, price):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user_row = await cursor.fetchone()
            if not user_row: return False 
            user_pk_id = user_row[0]

        cursor = await db.execute("DELETE FROM inventory WHERE id = ? AND user_id = ?", (inv_id, user_pk_id))
        if cursor.rowcount == 0:
            await db.commit()
            return False 
            
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (price, tg_user_id))
        await db.commit()
        return True

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT username, balance FROM users WHERE tg_id != 0 ORDER BY balance DESC LIMIT 10") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

# --- ФУНКЦИИ АДМИНА (ВЕРНУЛ ОБРАТНО) ---

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

async def admin_update_item_field(item_id, field, value):
    async with aiosqlite.connect(DB_NAME) as db:
        # Внимание: для простоты используем f-строку для имени поля, но value передаем параметром
        query = f"UPDATE items SET {field} = ? WHERE id = ?"
        await db.execute(query, (value, item_id))
        await db.commit()