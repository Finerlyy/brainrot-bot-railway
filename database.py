import aiosqlite
import sqlite3
import logging
import json
import random
from datetime import datetime

DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row 
        
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 5000, ip TEXT, cases_opened INTEGER DEFAULT 0, reg_date TEXT, photo_url TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER, icon_url TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, rarity TEXT, price INTEGER, image_url TEXT, sound_url TEXT, case_id INTEGER, FOREIGN KEY (case_id) REFERENCES cases(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS inventory (rowid INTEGER PRIMARY KEY, user_id INTEGER, item_id INTEGER, mutations TEXT DEFAULT '', FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES items(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS keys (user_id INTEGER, case_id INTEGER, quantity INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (case_id) REFERENCES cases(id), UNIQUE(user_id, case_id))")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY, 
                game_type TEXT, 
                wager_type TEXT, 
                wager_amount INTEGER, 
                wager_item_id INTEGER,
                host_id INTEGER, 
                guest_id INTEGER, 
                host_move TEXT, 
                guest_move TEXT, 
                winner_id INTEGER,
                status TEXT DEFAULT 'open'
            )
        """)

        await db.execute("CREATE TABLE IF NOT EXISTS rarity_weights (rarity TEXT PRIMARY KEY, weight INTEGER)")

        # МИГРАЦИИ
        try: await db.execute("ALTER TABLE users ADD COLUMN ip TEXT"); except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN cases_opened INTEGER DEFAULT 0"); except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN reg_date TEXT"); except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN photo_url TEXT"); except: pass
        try: await db.execute("ALTER TABLE inventory ADD COLUMN mutations TEXT DEFAULT ''"); except: pass

        default_weights = [('Common', 10000), ('Uncommon', 5000), ('Rare', 2500), ('Mythical', 500), ('Legendary', 100), ('Immortal', 20), ('Secret', 1)]
        await db.executemany("INSERT OR IGNORE INTO rarity_weights (rarity, weight) VALUES (?, ?)", default_weights)

        await db.commit()
        
        # НАПОЛНЕНИЕ
        case_name = '🧠 Ultimate Brainrot Case'
        case_price = 300
        case_icon = 'https://i.ibb.co/mCZ9d327/1000002237.jpg'
        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (case_name, case_price, case_icon))
        async with db.execute("SELECT id FROM cases WHERE name = ?", (case_name,)) as cur:
            row = await cur.fetchone()
            case_id = row[0] if row else None

        if case_id:
            async with db.execute("SELECT count(*) FROM items WHERE case_id = ?", (case_id,)) as cur:
                if (await cur.fetchone())[0] == 0:
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
                        await db.execute("INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", i)
                    await db.commit()

# --- ИГРОВЫЕ ФУНКЦИИ (ИСПРАВЛЕНО: использование индексов [0], [1]...) ---

async def create_game(tg_user_id, game_type, wager_type, wager_val, wager_item_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        # SELECT id, balance (0, 1)
        async with db.execute("SELECT id, balance FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return None
            uid = user[0]
            bal = user[1]

        if wager_type == 'balance':
            if bal < wager_val: return "no_balance"
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (wager_val, uid))
        elif wager_type == 'item':
            sql_check = "SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1"
            async with db.execute(sql_check, (uid, wager_item_id)) as cur:
                row = await cur.fetchone()
                if not row: return "no_item"
                inv_rowid = row[0]
            await db.execute("DELETE FROM inventory WHERE rowid = ?", (inv_rowid,))

        await db.execute("""
            INSERT INTO games (game_type, wager_type, wager_amount, wager_item_id, host_id, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        """, (game_type, wager_type, wager_val, wager_item_id, uid))
        await db.commit()
        return "ok"

async def get_open_games():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql = """
            SELECT g.*, u.username as host_name, i.name as item_name, i.image_url as item_img, i.rarity as item_rarity
            FROM games g
            JOIN users u ON g.host_id = u.id
            LEFT JOIN items i ON g.wager_item_id = i.id
            WHERE g.status = 'open'
            ORDER BY g.id DESC
        """
        async with db.execute(sql) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def join_game(game_id, tg_guest_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # SELECT id, balance (0, 1)
        async with db.execute("SELECT id, balance FROM users WHERE tg_id = ?", (tg_guest_id,)) as cursor:
            guest = await cursor.fetchone()
            guest_pk = guest[0]
            guest_bal = guest[1]

        # Explicitly select needed fields by index
        # 0: host_id, 1: status, 2: wager_type, 3: wager_amount, 4: wager_item_id
        sql_game = "SELECT host_id, status, wager_type, wager_amount, wager_item_id FROM games WHERE id = ?"
        async with db.execute(sql_game, (game_id,)) as cur:
            game = await cur.fetchone()
            if not game or game[1] != 'open': return "error"
            if game[0] == guest_pk: return "self"

            host_id = game[0]
            wager_type = game[2]
            wager_amount = game[3]
            wager_item_id = game[4]

        # Списание с гостя
        if wager_type == 'balance':
            if guest_bal < wager_amount: return "no_balance"
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (wager_amount, guest_pk))
        elif wager_type == 'item':
            sql_check = "SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1"
            async with db.execute(sql_check, (guest_pk, wager_item_id)) as cur:
                row = await cur.fetchone()
                if not row: return "no_item"
                inv_rowid = row[0]
            await db.execute("DELETE FROM inventory WHERE rowid = ?", (inv_rowid,))

        await db.execute("UPDATE games SET guest_id = ?, status = 'playing' WHERE id = ?", (guest_pk, game_id))
        await db.commit()
        return "ok"

async def make_move(game_id, tg_user_id, move):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u[0]

        # 0: host_id, 1: guest_id
        async with db.execute("SELECT host_id, guest_id FROM games WHERE id = ?", (game_id,)) as cur:
            game = await cur.fetchone()
            if not game: return "error"
            host_id = game[0]
        
        is_host = (user_pk == host_id)
        
        if is_host:
            await db.execute("UPDATE games SET host_move = ? WHERE id = ?", (move, game_id))
        else:
            await db.execute("UPDATE games SET guest_move = ? WHERE id = ?", (move, game_id))
        
        await db.commit()
        return await check_game_result(game_id)

async def check_game_result(game_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # Select all needed fields explicitly
        # 0: host_id, 1: guest_id, 2: host_move, 3: guest_move, 
        # 4: game_type, 5: wager_type, 6: wager_amount, 7: wager_item_id
        sql = "SELECT host_id, guest_id, host_move, guest_move, game_type, wager_type, wager_amount, wager_item_id FROM games WHERE id = ?"
        async with db.execute(sql, (game_id,)) as cur:
            game = await cur.fetchone()
        
        host_id = game[0]
        guest_id = game[1]
        h_move = game[2]
        g_move = game[3]
        g_type = game[4]
        w_type = game[5]
        w_amt = game[6]
        w_item = game[7]
        
        if not h_move or not g_move: return "waiting"
        
        winner_id = None
        
        if g_type == 'rps':
            if h_move == g_move: winner_id = 0
            elif (h_move=='rock' and g_move=='scissors') or \
                 (h_move=='scissors' and g_move=='paper') or \
                 (h_move=='paper' and g_move=='rock'):
                winner_id = host_id
            else:
                winner_id = guest_id
                
        elif g_type == 'even_odd':
            host_num = int(h_move)
            is_even = (host_num % 2 == 0)
            if (is_even and g_move == 'even') or (not is_even and g_move == 'odd'):
                winner_id = guest_id
            else:
                winner_id = host_id

        if winner_id == 0: 
            if w_type == 'balance':
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (w_amt, host_id))
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (w_amt, guest_id))
            else:
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (host_id, w_item))
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (guest_id, w_item))
        else:
            if w_type == 'balance':
                win_amt = w_amt * 2
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (win_amt, winner_id))
            else:
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (winner_id, w_item))
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (winner_id, w_item))

        await db.execute("UPDATE games SET status = 'finished', winner_id = ? WHERE id = ?", (winner_id, game_id))
        await db.commit()
        return "finished"

async def get_my_active_game(tg_user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return None
            uid = u[0]
            
        sql = """
            SELECT g.*, 
                   u1.username as host_name, 
                   u2.username as guest_name,
                   i.name as item_name, i.image_url as item_img
            FROM games g
            LEFT JOIN users u1 ON g.host_id = u1.id
            LEFT JOIN users u2 ON g.guest_id = u2.id
            LEFT JOIN items i ON g.wager_item_id = i.id
            WHERE (g.host_id = ? OR g.guest_id = ?) AND g.status != 'finished'
        """
        async with db.execute(sql, (uid, uid)) as cur:
            row = await cur.fetchone()
            if row:
                d = dict(row)
                d['is_host'] = (d['host_id'] == uid)
                return d
            return None

# --- ИНВЕНТАРЬ ---

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
    await add_items_with_mutations(tg_user_id, [item])

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

async def delete_one_item_by_id(tg_user_id, item_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u[0]
        await db.execute("DELETE FROM inventory WHERE rowid IN (SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1)", (user_pk, item_id))
        await db.commit()
        return True

async def sell_items_batch_db(tg_user_id, item_id, count, total_price):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u[0]

        sql = "DELETE FROM inventory WHERE rowid IN (SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? LIMIT ?)"
        await db.execute(sql, (user_pk, item_id, count))
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (total_price, tg_user_id))
        await db.commit()
        return True

# --- BASIC USER & ITEMS ---

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
            except: pass
            async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
                user = await cursor.fetchone()
        return user

async def get_profile_stats(tg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return {}
            user_pk = user[0]
        sql_best = "SELECT i.name, i.price, i.image_url, i.rarity FROM inventory inv JOIN items i ON inv.item_id = i.id WHERE inv.user_id = ? ORDER BY i.price DESC LIMIT 1"
        best_item = None
        async with db.execute(sql_best, (user_pk,)) as cur:
            row = await cur.fetchone()
            if row: best_item = dict(row)
        sql_sum = "SELECT SUM(i.price) FROM inventory inv JOIN items i ON inv.item_id = i.id WHERE inv.user_id = ?"
        inv_value = 0
        async with db.execute(sql_sum, (user_pk,)) as cur:
            row = await cur.fetchone()
            if row and row[0]: inv_value = row[0]
        return {"best_item": best_item, "inv_value": inv_value}

async def update_user_photo(tg_id, photo_url):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET photo_url = ? WHERE tg_id = ?", (photo_url, tg_id))
        await db.commit()

async def get_public_profile(target_tg_id):
    user = await get_user(target_tg_id, "Unknown")
    stats = await get_profile_stats(target_tg_id)
    if not user: return None
    user_dict = dict(user)
    user_dict['best_item'] = stats.get('best_item')
    user_dict['net_worth'] = user_dict['balance'] + (stats.get('inv_value') or 0)
    return user_dict

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
        async with db.execute("SELECT * FROM cases") as cursor: return await cursor.fetchall()

async def get_case_data(case_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)) as cursor: return await cursor.fetchone()

async def get_case_items(case_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql = "SELECT * FROM items" if case_id is None else "SELECT * FROM items WHERE case_id = ?"
        params = () if case_id is None else (case_id,)
        async with db.execute(sql, params) as cursor: return await cursor.fetchall()

async def get_all_items_sorted():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM items ORDER BY price ASC") as cursor: return await cursor.fetchall()

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT username, balance, tg_id, photo_url FROM users WHERE tg_id != 0 ORDER BY balance DESC LIMIT 10") as cursor:
            return [dict(row) if hasattr(row, 'keys') else {'username': row[0], 'balance': row[1]} for row in await cursor.fetchall()]

async def admin_get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM users WHERE tg_id != 0") as cursor: return await cursor.fetchall()

async def add_keys_to_user(tg_user_id, case_id, quantity):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u[0]
        await db.execute("INSERT INTO keys (user_id, case_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, case_id) DO UPDATE SET quantity = quantity + ?", (user_pk, case_id, quantity, quantity))
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
            if not row or row[0] < quantity: return False
        await db.execute("UPDATE keys SET quantity = quantity - ? WHERE user_id = ? AND case_id = ?", (quantity, user_pk, case_id))
        await db.commit()
        return True

async def get_rarity_weights():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT rarity, weight FROM rarity_weights") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

async def set_rarity_weight(rarity, weight):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO rarity_weights (rarity, weight) VALUES (?, ?) ON CONFLICT(rarity) DO UPDATE SET weight = ?", (rarity, weight, weight))
        await db.commit()

# Admin helpers
async def get_item_by_id(item_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor: return await cursor.fetchone()

async def get_case_by_id(case_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)) as cursor: return await cursor.fetchone()

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