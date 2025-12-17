import aiosqlite
import sqlite3
import logging
import json
import random
import time
from datetime import datetime

DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row 
        
        # Обновляем таблицу users, добавляем brainrot_coins
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 5000, brainrot_coins INTEGER DEFAULT 0, ip TEXT, cases_opened INTEGER DEFAULT 0, reg_date TEXT, photo_url TEXT)")
        
        await db.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER, icon_url TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, rarity TEXT, price INTEGER, image_url TEXT, sound_url TEXT, case_id INTEGER, FOREIGN KEY (case_id) REFERENCES cases(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS inventory (rowid INTEGER PRIMARY KEY, user_id INTEGER, item_id INTEGER, mutations TEXT DEFAULT '', FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES items(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS keys (user_id INTEGER, case_id INTEGER, quantity INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (case_id) REFERENCES cases(id), UNIQUE(user_id, case_id))")
        
        # Таблица Инкубатора
        await db.execute("""
            CREATE TABLE IF NOT EXISTS incubator (
                user_id INTEGER PRIMARY KEY, 
                item_id INTEGER, 
                mutations TEXT,
                start_time INTEGER, 
                last_claim_time INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (item_id) REFERENCES items(id)
            )
        """)

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

        # --- МИГРАЦИИ ---
        try: await db.execute("ALTER TABLE users ADD COLUMN brainrot_coins INTEGER DEFAULT 0")
        except: pass
        
        cols = ["ip", "cases_opened", "reg_date", "photo_url"]
        for col in cols:
            try: await db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT") 
            except: pass
        
        try: await db.execute("ALTER TABLE inventory ADD COLUMN mutations TEXT DEFAULT ''")
        except: pass

        default_weights = [('Common', 10000), ('Uncommon', 5000), ('Rare', 2500), ('Mythical', 500), ('Legendary', 100), ('Immortal', 20), ('Secret', 1)]
        await db.executemany("INSERT OR IGNORE INTO rarity_weights (rarity, weight) VALUES (?, ?)", default_weights)

        await db.commit()
        
        # Наполнение
        case_name = '🧠 Ultimate Brainrot Case'
        case_price = 300
        case_icon = 'https://i.ibb.co/mCZ9d327/1000002237.jpg'
        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (case_name, case_price, case_icon))
        async with db.execute("SELECT id FROM cases WHERE name = ?", (case_name,)) as cur:
            row = await cur.fetchone()
            case_id = row['id'] if row else None

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

# --- ФУНКЦИИ ИНВЕНТАРЯ ---

async def add_items_with_mutations(tg_user_id, items_list):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user_row = await cursor.fetchone()
            if not user_row: return
            user_pk = user_row['id']
            
        insert_data = []
        for item in items_list:
            i_id = item.get('id') if isinstance(item, dict) else item[0]
            muts = item.get('mutations', [])
            muts_str = ",".join(muts) if muts else ""
            insert_data.append((user_pk, i_id, muts_str))

        await db.executemany("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?, ?, ?)", insert_data)
        await db.commit()

async def get_inventory_grouped(user_id_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (user_id_tg,)) as cursor:
            u = await cursor.fetchone()
            if not u: return []
            user_pk = u['id']

        # Группируем для отображения, но для действий нужны уникальные ID (rowid)
        # Для UI мы просто считаем количество, а для выбора конкретного предмета (инкубатор)
        # будем использовать другой запрос или передавать sample rowid
        sql = """
            SELECT i.id as item_id, i.name, i.rarity, i.image_url, i.price, inv.mutations, COUNT(inv.item_id) as quantity, MAX(inv.rowid) as sample_id
            FROM inventory AS inv 
            JOIN items AS i ON inv.item_id = i.id 
            WHERE inv.user_id = ?
            GROUP BY i.id, i.name, i.rarity, i.image_url, i.price, inv.mutations
        """
        async with db.execute(sql, (user_pk,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def get_specific_item_instance(tg_user_id, item_id, mutations_str):
    # Получить один конкретный rowid для предмета
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']
        
        sql = "SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? AND mutations = ? LIMIT 1"
        async with db.execute(sql, (user_pk, item_id, mutations_str)) as cur:
            row = await cur.fetchone()
            return row['rowid'] if row else None

async def sell_specific_item_stack(tg_user_id, item_id, mutations_str, count, total_price):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u['id']

        sql = """
            DELETE FROM inventory 
            WHERE rowid IN (
                SELECT rowid FROM inventory 
                WHERE user_id = ? AND item_id = ? AND mutations = ?
                LIMIT ?
            )
        """
        await db.execute(sql, (user_pk, item_id, mutations_str, count))
        if total_price > 0:
            await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id = ?", (total_price, tg_user_id))
        await db.commit()
        return True

# --- ИНКУБАТОР (НОВОЕ) ---

async def get_incubator_status(tg_user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']
        
        sql = """
            SELECT inc.*, i.name, i.image_url, i.price, i.rarity
            FROM incubator inc
            JOIN items i ON inc.item_id = i.id
            WHERE inc.user_id = ?
        """
        async with db.execute(sql, (user_pk,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def put_in_incubator(tg_user_id, item_id, mutations_str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']

        # Проверка, пуст ли инкубатор
        async with db.execute("SELECT 1 FROM incubator WHERE user_id = ?", (user_pk,)) as cur:
            if await cur.fetchone(): return "busy"

        # Ищем предмет в инвентаре (конкретный экземпляр)
        sql_find = "SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? AND mutations = ? LIMIT 1"
        async with db.execute(sql_find, (user_pk, item_id, mutations_str)) as cur:
            row = await cur.fetchone()
            if not row: return "no_item"
            inv_rowid = row['rowid']

        # Удаляем из инвентаря
        await db.execute("DELETE FROM inventory WHERE rowid = ?", (inv_rowid,))
        
        # Кладем в инкубатор
        now = int(time.time())
        await db.execute(
            "INSERT INTO incubator (user_id, item_id, mutations, start_time, last_claim_time) VALUES (?, ?, ?, ?, ?)",
            (user_pk, item_id, mutations_str, now, now)
        )
        await db.commit()
        return "ok"

async def claim_incubator(tg_user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']
        
        sql = """
            SELECT inc.*, i.price 
            FROM incubator inc 
            JOIN items i ON inc.item_id = i.id 
            WHERE inc.user_id = ?
        """
        async with db.execute(sql, (user_pk,)) as cur:
            inc = await cur.fetchone()
            if not inc: return 0
        
        now = int(time.time())
        elapsed_seconds = now - inc['last_claim_time']
        if elapsed_seconds < 10: return 0 # Анти-спам

        # Расчет фарма:
        # База: 10% от цены предмета в день (24 часа)
        # Мутации увеличивают базу.
        base_price = inc['price']
        
        # Парсим мутации
        muts_str = inc['mutations']
        muts = muts_str.split(',') if muts_str else []
        multiplier = 1.0
        
        # Импортируем множители (дублируем логику, чтобы не зависеть от bot.py)
        MUTATION_MULTS = {'Gold': 1.1, 'Diamond': 1.2, 'Bloodrot': 1.5, 'Candy': 1.5, 'Rainbow': 2.0, 'Galaxy': 3.0}
        for m in muts:
            multiplier *= MUTATION_MULTS.get(m, 1.0)
            
        coins_per_day = base_price * multiplier * 0.10 # 10% в день
        coins_per_second = coins_per_day / 86400
        
        farmed = coins_per_second * elapsed_seconds
        
        if farmed > 0:
            # Обновляем таймер
            await db.execute("UPDATE incubator SET last_claim_time = ? WHERE user_id = ?", (now, user_pk))
            # Начисляем дробные? Нет, храним int, копим остаток?
            # Проще начислять int, теряя копейки (brainrot logic)
            coins_to_add = int(farmed)
            if coins_to_add > 0:
                await db.execute("UPDATE users SET brainrot_coins = brainrot_coins + ? WHERE id = ?", (coins_to_add, user_pk))
                await db.commit()
                return coins_to_add
        
        await db.commit()
        return 0

async def take_from_incubator(tg_user_id):
    await claim_incubator(tg_user_id) # Сначала собираем остатки
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']
            
        async with db.execute("SELECT * FROM incubator WHERE user_id = ?", (user_pk,)) as cur:
            inc = await cur.fetchone()
            if not inc: return "empty"
            
        # Возвращаем в инвентарь
        await db.execute("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?, ?, ?)", (user_pk, inc['item_id'], inc['mutations']))
        # Удаляем из инкубатора
        await db.execute("DELETE FROM incubator WHERE user_id = ?", (user_pk,))
        await db.commit()
        return "ok"

# --- АДМИНСКИЕ ФУНКЦИИ (ОБНОВЛЕННЫЕ) ---

async def admin_get_user_inventory_detailed(tg_user_id):
    # Возвращает список всех предметов с их УНИКАЛЬНЫМИ ID (rowid)
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return []
            user_pk = u['id']
            
        sql = """
            SELECT inv.rowid as unique_id, i.name, i.rarity, inv.mutations 
            FROM inventory inv
            JOIN items i ON inv.item_id = i.id
            WHERE inv.user_id = ?
        """
        async with db.execute(sql, (user_pk,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

async def admin_update_inventory_mutation(unique_inv_id, new_mutations_str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE inventory SET mutations = ? WHERE rowid = ?", (new_mutations_str, unique_inv_id))
        await db.commit()
        return True

async def update_user_brc(tg_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET brainrot_coins = brainrot_coins + ? WHERE tg_id = ?", (amount, tg_id))
        await db.commit()

# --- ОСТАЛЬНЫЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ ИЛИ С НЕБОЛЬШИМИ ПРАВКАМИ) ---

async def create_game(tg_user_id, game_type, wager_type, wager_val, wager_item_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id, balance FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return None
            uid = user['id']
            balance = user['balance']

        if wager_type == 'balance':
            if balance < wager_val: return "no_balance"
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (wager_val, uid))
        elif wager_type == 'item':
            sql_check = "SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1"
            async with db.execute(sql_check, (uid, wager_item_id)) as cur:
                row = await cur.fetchone()
                if not row: return "no_item"
                inv_rowid = row['rowid']
            await db.execute("DELETE FROM inventory WHERE rowid = ?", (inv_rowid,))

        await db.execute("""
            INSERT INTO games (game_type, wager_type, wager_amount, wager_item_id, host_id, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        """, (game_type, wager_type, wager_val, wager_item_id, uid))
        await db.commit()
        return "ok"

async def cancel_game_db(game_id, tg_user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']

        async with db.execute("SELECT * FROM games WHERE id = ?", (game_id,)) as cur:
            game = await cur.fetchone()
            if not game: return "not_found"
        
        if game['status'] == 'finished':
             await db.execute("DELETE FROM games WHERE id = ?", (game_id,))
             await db.commit()
             return "ok"

        if game['host_id'] != user_pk: return "not_host"
        if game['status'] != 'open': return "started"

        if game['wager_type'] == 'balance':
            await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (game['wager_amount'], user_pk))
        elif game['wager_type'] == 'item':
            await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (user_pk, game['wager_item_id']))

        await db.execute("DELETE FROM games WHERE id = ?", (game_id,))
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
        db.row_factory = sqlite3.Row
        
        async with db.execute("SELECT id, balance FROM users WHERE tg_id = ?", (tg_guest_id,)) as cursor:
            guest = await cursor.fetchone()
            if not guest: return "user_not_found"
            guest_pk = guest['id']
            guest_bal = guest['balance']

        async with db.execute("SELECT * FROM games WHERE id = ?", (game_id,)) as cur:
            game = await cur.fetchone()
            if not game: return "game_not_found"
            if game['status'] != 'open': return "game_not_open"
            if game['host_id'] == guest_pk: return "self_join_error"

        if game['wager_type'] == 'balance':
            if guest_bal < game['wager_amount']: return "no_balance"
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (game['wager_amount'], guest_pk))
        elif game['wager_type'] == 'item':
            sql_check = "SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1"
            async with db.execute(sql_check, (guest_pk, game['wager_item_id'])) as cur:
                row = await cur.fetchone()
                if not row: return "no_item"
                inv_rowid = row['rowid']
            await db.execute("DELETE FROM inventory WHERE rowid = ?", (inv_rowid,))

        await db.execute("UPDATE games SET guest_id = ?, status = 'playing' WHERE id = ?", (guest_pk, game_id))
        await db.commit()
        return "ok"

async def make_move(game_id, tg_user_id, move):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']

        async with db.execute("SELECT * FROM games WHERE id = ?", (game_id,)) as cur:
            game = await cur.fetchone()
        
        if not game: return "error"
        
        is_host = (user_pk == game['host_id'])
        
        if is_host:
            await db.execute("UPDATE games SET host_move = ? WHERE id = ?", (move, game_id))
        else:
            await db.execute("UPDATE games SET guest_move = ? WHERE id = ?", (move, game_id))
        
        await db.commit()
        return await check_game_result(game_id)

async def check_game_result(game_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM games WHERE id = ?", (game_id,)) as cur:
            game = await cur.fetchone()
        
        h_move = game['host_move']
        g_move = game['guest_move']
        
        if not h_move or not g_move: return "waiting"
        
        winner_id = None
        host_id = game['host_id']
        guest_id = game['guest_id']
        
        if game['game_type'] == 'rps':
            if h_move == g_move: winner_id = 0
            elif (h_move=='rock' and g_move=='scissors') or \
                 (h_move=='scissors' and g_move=='paper') or \
                 (h_move=='paper' and g_move=='rock'):
                winner_id = host_id
            else:
                winner_id = guest_id
                
        elif game['game_type'] == 'even_odd':
            host_num = int(h_move)
            is_even = (host_num % 2 == 0)
            if (is_even and g_move == 'even') or (not is_even and g_move == 'odd'):
                winner_id = guest_id
            else:
                winner_id = host_id

        if winner_id == 0: 
            if game['wager_type'] == 'balance':
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (game['wager_amount'], host_id))
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (game['wager_amount'], guest_id))
            else:
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (host_id, game['wager_item_id']))
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (guest_id, game['wager_item_id']))
        else:
            if game['wager_type'] == 'balance':
                win_amt = game['wager_amount'] * 2
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (win_amt, winner_id))
            else:
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (winner_id, game['wager_item_id']))
                await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (winner_id, game['wager_item_id']))

        await db.execute("UPDATE games SET status = 'finished', winner_id = ? WHERE id = ?", (winner_id, game_id))
        await db.commit()
        return "finished"

async def get_my_active_game(tg_user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return None
            uid = u['id']
            
        sql = """
            SELECT g.*, 
                   u1.username as host_name, 
                   u2.username as guest_name,
                   u1.tg_id as host_tg_id,
                   u2.tg_id as guest_tg_id,
                   i.name as item_name, i.image_url as item_img
            FROM games g
            LEFT JOIN users u1 ON g.host_id = u1.id
            LEFT JOIN users u2 ON g.guest_id = u2.id
            LEFT JOIN items i ON g.wager_item_id = i.id
            WHERE (g.host_id = ? OR g.guest_id = ?) 
            ORDER BY g.id DESC LIMIT 1
        """
        async with db.execute(sql, (uid, uid)) as cur:
            row = await cur.fetchone()
            if row:
                d = dict(row)
                return d
            return None

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
            user_pk = user['id']
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
            return row['ip'] if row else None

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

async def add_specific_item_by_id(tg_user_id, item_id, quantity=1):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user_row = await cursor.fetchone()
            if not user_row: return False
            user_pk_id = user_row['id']
        insert_data = [(user_pk_id, item_id) for _ in range(quantity)]
        await db.executemany("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", insert_data)
        await db.commit()
        return True

async def add_item_to_inventory(tg_user_id, item):
    await add_items_with_mutations(tg_user_id, [item])

async def delete_one_item_by_id(tg_user_id, item_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            user_pk = u['id']
        await db.execute("DELETE FROM inventory WHERE rowid IN (SELECT rowid FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1)", (user_pk, item_id))
        await db.commit()
        return True

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql = """
        SELECT u.username, u.photo_url, u.tg_id, u.balance, u.brainrot_coins,
               (u.balance + COALESCE((SELECT SUM(i.price) 
                                      FROM inventory inv 
                                      JOIN items i ON inv.item_id = i.id 
                                      WHERE inv.user_id = u.id), 0)) as net_worth
        FROM users u
        WHERE u.tg_id != 0
        ORDER BY net_worth DESC
        LIMIT 10
        """
        async with db.execute(sql) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def admin_get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM users WHERE tg_id != 0") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def add_keys_to_user(tg_user_id, case_id, quantity):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u['id']
        await db.execute("INSERT INTO keys (user_id, case_id, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, case_id) DO UPDATE SET quantity = quantity + ?", (user_pk, case_id, quantity, quantity))
        await db.commit()
        return True

async def get_user_keys(tg_user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return {}
            user_pk = u['id']
        async with db.execute("SELECT case_id, quantity FROM keys WHERE user_id = ? AND quantity > 0", (user_pk,)) as cursor:
            rows = await cursor.fetchall()
            return {row['case_id']: row['quantity'] for row in rows}

async def use_keys(tg_user_id, case_id, quantity):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            u = await cursor.fetchone()
            if not u: return False
            user_pk = u['id']
        async with db.execute("SELECT quantity FROM keys WHERE user_id = ? AND case_id = ?", (user_pk, case_id)) as cursor:
            row = await cursor.fetchone()
            if not row or row['quantity'] < quantity: return False
        await db.execute("UPDATE keys SET quantity = quantity - ? WHERE user_id = ? AND case_id = ?", (quantity, user_pk, case_id))
        await db.commit()
        return True

async def get_rarity_weights():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT rarity, weight FROM rarity_weights") as cursor:
            rows = await cursor.fetchall()
            return {row['rarity']: row['weight'] for row in rows}

async def set_rarity_weight(rarity, weight):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO rarity_weights (rarity, weight) VALUES (?, ?) ON CONFLICT(rarity) DO UPDATE SET weight = ?", (rarity, weight, weight))
        await db.commit()

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