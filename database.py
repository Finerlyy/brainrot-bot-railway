import aiosqlite
import sqlite3
import logging
from datetime import datetime

DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row 
        
        # Создаем таблицы
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 5000, ip TEXT, cases_opened INTEGER DEFAULT 0, reg_date TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER, icon_url TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, rarity TEXT, price INTEGER, image_url TEXT, sound_url TEXT, case_id INTEGER, FOREIGN KEY (case_id) REFERENCES cases(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, item_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES items(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS keys (user_id INTEGER, case_id INTEGER, quantity INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (case_id) REFERENCES cases(id), UNIQUE(user_id, case_id))")

        # --- МИГРАЦИИ (Обновляем старую базу) ---
        try: await db.execute("ALTER TABLE users ADD COLUMN ip TEXT")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN cases_opened INTEGER DEFAULT 0")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN reg_date TEXT")
        except: pass

        await db.commit()
        
        # НАПОЛНЕНИЕ
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
                ('SECRET ITEM', 'Secret', 50000, 'https://cdn-icons-png.flaticon.com/512/5726/5726775.png', '-', case_id),
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
                now = datetime.now().isoformat()
                await db.execute("INSERT INTO users (tg_id, username, reg_date) VALUES (?, ?, ?)", (tg_id, username, now))
                await db.commit()
            except sqlite3.IntegrityError: pass
            async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
                user = await cursor.fetchone()
        return user

async def get_profile_stats(tg_id):
    """Считает стоимость инвентаря и находит лучший предмет"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        # Получаем внутренний ID
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return {}
            user_pk = user[0]

        # Лучший предмет
        sql_best = """
            SELECT i.name, i.price, i.image_url, i.rarity 
            FROM inventory inv
            JOIN items i ON inv.item_id = i.id
            WHERE inv.user_id = ?
            ORDER BY i.price DESC
            LIMIT 1
        """
        best_item = None
        async with db.execute(sql_best, (user_pk,)) as cur:
            row = await cur.fetchone()
            if row: best_item = dict(row)

        # Стоимость инвентаря
        sql_sum = """
            SELECT SUM(i.price) 
            FROM inventory inv
            JOIN items i ON inv.item_id = i.id
            WHERE inv.user_id = ?
        """
        inv_value = 0
        async with db.execute(sql_sum, (user_pk,)) as cur:
            row = await cur.fetchone()
            if row and row[0]: inv_value = row[0]

        return {"best_item": best_item, "inv_value": inv_value}

async def increment_cases_opened(tg_id, count):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET cases_opened = cases_opened + ? WHERE tg_id = ?", (count, tg_id))
        await db.commit()

async def update_user_ip(tg_id, ip_address):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ip = ? WHERE tg_id = ?", (ip_address, tg_id))
        await db.commit()

async def get_user_ip(tg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT ip FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

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

async def add_specific_item_by_id(tg_user_id, item_id, quantity=1):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user_row = await cursor.fetchone()
            if not user_row: return False
            user_pk_id = user_row[0]
        
        insert_data = [(user_pk_id, item_id) for _ in range(quantity)]
        await db.executemany("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", insert_data)
        await db.commit()
        return True

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

async def add_keys_to_user(tg_user_id, case_id, quantity):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u[0]
            
        await db.execute("""
            INSERT INTO keys (user_id, case_id, quantity) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, case_id) 
            DO UPDATE SET quantity = quantity + ?
        """, (user_pk, case_id, quantity, quantity))
        await db.commit()
        return True

async def get_user_keys(tg_user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return {}
            user_pk = u[0]
            
        async with db.execute("SELECT case_id, quantity FROM keys WHERE user_id = ? AND quantity > 0", (user_pk,)) as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

async def use_keys(tg_user_id, case_id, quantity):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u[0]
            
        async with db.execute("SELECT quantity FROM keys WHERE user_id = ? AND case_id = ?", (user_pk, case_id)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] < quantity:
                return False
                
        await db.execute("UPDATE keys SET quantity = quantity - ? WHERE user_id = ? AND case_id = ?", (quantity, user_pk, case_id))
        await db.commit()
        return True

async def get_item_by_id(item_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            return await cursor.fetchone()

async def get_case_by_id(case_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)) as cursor:
            return await cursor.fetchone()

async def admin_update_field(table, record_id, field, value):
    allowed_fields = ['name', 'price', 'icon_url', 'image_url', 'rarity', 'case_id', 'sound_url']
    if field not in allowed_fields: return False
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE {table} SET {field} = ? WHERE id = ?", (value, record_id))
        await db.commit()
        return True

async def admin_add_case(name, price, url):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (name, price, url))
        await db.commit()

async def admin_del_case(case_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM items WHERE case_id = ?", (case_id,))
        await db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        await db.commit()

async def admin_add_item(case_id, name, rarity, price, url):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", (name, rarity, price, url, '-', case_id))
        await db.commit()

async def admin_del_item(item_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()