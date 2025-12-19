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
        
        # БАЛАНС 0 ПО УМОЛЧАНИЮ
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 0, ip TEXT, cases_opened INTEGER DEFAULT 0, reg_date TEXT, photo_url TEXT, last_claim INTEGER DEFAULT 0)")
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
                wager_mutations TEXT DEFAULT '',
                guest_mutations TEXT DEFAULT '',
                host_id INTEGER, 
                guest_id INTEGER, 
                host_move TEXT, 
                guest_move TEXT, 
                winner_id INTEGER,
                status TEXT DEFAULT 'open'
            )
        """)

        await db.execute("CREATE TABLE IF NOT EXISTS rarity_weights (rarity TEXT PRIMARY KEY, weight INTEGER)")

        # Миграции
        try: await db.execute("ALTER TABLE games ADD COLUMN wager_mutations TEXT DEFAULT ''")
        except: pass
        try: await db.execute("ALTER TABLE games ADD COLUMN guest_mutations TEXT DEFAULT ''")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN photo_url TEXT")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN last_claim INTEGER DEFAULT 0")
        except: pass

        default_weights = [('Common', 10000), ('Uncommon', 5000), ('Rare', 2500), ('Mythical', 500), ('Legendary', 100), ('Immortal', 20), ('Secret', 1)]
        await db.executemany("INSERT OR IGNORE INTO rarity_weights (rarity, weight) VALUES (?, ?)", default_weights)
        await db.commit()
        
        # --- КЕЙСЫ ---
        case_name = '🧠 Brainrot Case'
        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (case_name, 300, 'https://i.ibb.co/Kcph3txZ/123-Photoroom.png'))
        
        free_case_name = '🎁 Free Box'
        await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (free_case_name, 0, 'https://cdn-icons-png.flaticon.com/512/669/669954.png'))

        async with db.execute("SELECT id FROM cases WHERE name = ?", (case_name,)) as cur:
            row = await cur.fetchone()
            main_case_id = row['id'] if row else 1
        async with db.execute("SELECT id FROM cases WHERE name = ?", (free_case_name,)) as cur:
            row = await cur.fetchone()
            free_case_id = row['id'] if row else 2
            
        async with db.execute("SELECT count(*) FROM items WHERE case_id = ?", (main_case_id,)) as cur:
            if (await cur.fetchone())[0] == 0:
                items_data = [
                    ('Lirili Bat Guy', 'Common', 100, 'https://i.imgur.com/vZkT4cu.jpeg', '-', main_case_id),
                    ('Tung Tung Elephant', 'Common', 150, 'https://i.imgur.com/4RtWcWY.jpeg', '-', main_case_id),
                    ('Tatata Teapot', 'Uncommon', 400, 'https://i.imgur.com/DZDL8RI.jpeg', '-', main_case_id),
                    ('Tralala Shark', 'Rare', 1200, 'https://i.imgur.com/iDcJaMp.jpeg', '-', main_case_id),
                    ('Orcalero Orca', 'Mythical', 3500, 'https://i.imgur.com/EsqyjjW.jpeg', '-', main_case_id),
                    ('Chimpanzini Bananini', 'Mythical', 10000, 'https://i.imgur.com/0QTbLT8.jpeg', '-', main_case_id),
                    ('SECRET ITEM', 'Secret', 50000, 'https://cdn-icons-png.flaticon.com/512/5726/5726775.png', '-', main_case_id),
                ]
                for i in items_data:
                    await db.execute("INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", i)
        
        async with db.execute("SELECT count(*) FROM items WHERE case_id = ?", (free_case_id,)) as cur:
            if (await cur.fetchone())[0] == 0:
                items_data_free = [
                    ('Air', 'Common', 1, 'https://cdn-icons-png.flaticon.com/512/262/262523.png', '-', free_case_id),
                    ('Dust', 'Common', 5, 'https://cdn-icons-png.flaticon.com/512/866/866953.png', '-', free_case_id),
                    ('Old Boot', 'Uncommon', 50, 'https://cdn-icons-png.flaticon.com/512/2669/2669698.png', '-', free_case_id),
                    ('Lucky Coin', 'Rare', 500, 'https://cdn-icons-png.flaticon.com/512/1042/1042562.png', '-', free_case_id),
                ]
                for i in items_data_free:
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
                now = datetime.now().isoformat()
                await db.execute("INSERT INTO users (tg_id, username, reg_date) VALUES (?, ?, ?)", (tg_id, username, now))
                await db.commit()
                async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor: user = await cursor.fetchone()
            except: pass
        return user

async def get_profile_stats(uid_tg):
    """Возвращает статистику профиля (ценность инвентаря и лучший предмет)"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id=?", (uid_tg,)) as c:
            row = await c.fetchone()
            if not row: return {"best_item": None, "inv_value": 0}
            pk = row[0]
            
        sql_val = "SELECT SUM(items.price) FROM inventory JOIN items ON inventory.item_id = items.id WHERE inventory.user_id = ?"
        async with db.execute(sql_val, (pk,)) as c:
            inv_value = (await c.fetchone())[0] or 0
            
        best_item = await get_best_item_db(pk)
        return {"best_item": best_item, "inv_value": inv_value}

async def get_best_item_db(user_pk):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql_best = """
            SELECT i.name, i.price, i.image_url, i.rarity 
            FROM inventory inv 
            JOIN items i ON inv.item_id = i.id 
            WHERE inv.user_id = ? 
            ORDER BY 
                CASE i.rarity 
                    WHEN 'Secret' THEN 7 
                    WHEN 'Immortal' THEN 6 
                    WHEN 'Legendary' THEN 5 
                    WHEN 'Mythical' THEN 4 
                    WHEN 'Rare' THEN 3 
                    WHEN 'Uncommon' THEN 2 
                    ELSE 1 
                END DESC,
                i.price DESC 
            LIMIT 1
        """
        async with db.execute(sql_best, (user_pk,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

# --- ФУНКЦИИ ИНВЕНТАРЯ И КЕЙСОВ ---

async def add_items_with_mutations(uid_tg, items):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id=?", (uid_tg,)) as c:
            row = await c.fetchone()
            if not row: return
            pk = row[0]
        data = [(pk, i.get('id'), ",".join(i.get('mutations', []))) for i in items]
        await db.executemany("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?,?,?)", data)
        await db.commit()

async def add_item_to_inventory(uid_tg, item):
    await add_items_with_mutations(uid_tg, [item])

async def delete_one_item_by_id(uid_tg, iid):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id=?", (uid_tg,)) as c:
            row = await c.fetchone()
            if not row: return
            pk = row[0]
        await db.execute("DELETE FROM inventory WHERE rowid IN (SELECT rowid FROM inventory WHERE user_id=? AND item_id=? LIMIT 1)", (pk, iid))
        await db.commit()

async def get_inventory_grouped(user_id_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id = ?", (user_id_tg,)) as cursor:
            u = await cursor.fetchone()
            if not u: return []
            user_pk = u['id']
        sql = """SELECT i.id as item_id, i.name, i.rarity, i.image_url, i.price, inv.mutations, COUNT(inv.item_id) as quantity FROM inventory AS inv JOIN items AS i ON inv.item_id = i.id WHERE inv.user_id = ? GROUP BY i.id, i.name, i.rarity, i.image_url, i.price, inv.mutations"""
        async with db.execute(sql, (user_pk,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def claim_free_case_key(tg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id, last_claim FROM users WHERE tg_id = ?", (tg_id,)) as cur:
            u = await cur.fetchone()
            if not u: return "error"
            uid, last = u['id'], u['last_claim']
        now = int(time.time())
        if now - last < 172800: return "too_early"
        async with db.execute("SELECT id FROM cases WHERE name = '🎁 Free Box'") as cur:
            row = await cur.fetchone()
            if not row: return "no_case"
            cid = row['id']
        await db.execute("INSERT INTO keys (user_id, case_id, quantity) VALUES (?,?,1) ON CONFLICT(user_id, case_id) DO UPDATE SET quantity=quantity+1", (uid, cid))
        await db.execute("UPDATE users SET last_claim = ? WHERE id = ?", (now, uid))
        await db.commit()
        return "ok"

# --- ИГРЫ ---

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql="""SELECT username, photo_url, tg_id, balance, (balance + COALESCE((SELECT SUM(items.price) FROM inventory JOIN items ON inventory.item_id=items.id WHERE inventory.user_id=users.id),0)) as net_worth FROM users WHERE tg_id!=0 ORDER BY net_worth DESC LIMIT 10"""
        async with db.execute(sql) as c: return [dict(r) for r in await c.fetchall()]

async def get_open_games():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        sql="""SELECT g.*, u.username as host_name, i.name as item_name, i.image_url as item_img, i.rarity as item_rarity FROM games g JOIN users u ON g.host_id=u.id LEFT JOIN items i ON g.wager_item_id=i.id WHERE g.status='open' ORDER BY g.id DESC"""
        async with db.execute(sql) as c: return [dict(r) for r in await c.fetchall()]

async def create_game(tg_user_id, game_type, wager_type, wager_val, wager_item_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id, balance FROM users WHERE tg_id = ?", (tg_user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return "error"
            uid = user['id']
        mutations_str = ""
        if wager_type == 'balance':
            if user['balance'] < wager_val: return "no_balance"
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (wager_val, uid))
        elif wager_type == 'item':
            sql_check = "SELECT rowid, mutations FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1"
            async with db.execute(sql_check, (uid, wager_item_id)) as cur:
                row = await cur.fetchone()
                if not row: return "no_item"
                inv_rowid, mutations_str = row['rowid'], row['mutations']
            await db.execute("DELETE FROM inventory WHERE rowid = ?", (inv_rowid,))
        await db.execute("INSERT INTO games (game_type, wager_type, wager_amount, wager_item_id, wager_mutations, host_id, status) VALUES (?, ?, ?, ?, ?, ?, 'open')", (game_type, wager_type, wager_val, wager_item_id, mutations_str, uid))
        await db.commit()
        return "ok"

async def join_game(game_id, tg_guest_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id, balance FROM users WHERE tg_id = ?", (tg_guest_id,)) as cursor:
            guest = await cursor.fetchone()
            if not guest: return "error"
            guest_pk = guest['id']
        async with db.execute("SELECT * FROM games WHERE id = ?", (game_id,)) as cur:
            game = await cur.fetchone()
            if not game or game['status'] != 'open': return "game_not_open"
            if game['host_id'] == guest_pk: return "self_join_error"
        guest_muts = ""
        if game['wager_type'] == 'balance':
            if guest['balance'] < game['wager_amount']: return "no_balance"
            await db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (game['wager_amount'], guest_pk))
        elif game['wager_type'] == 'item':
            sql_check = "SELECT rowid, mutations FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1"
            async with db.execute(sql_check, (guest_pk, game['wager_item_id'])) as cur:
                row = await cur.fetchone()
                if not row: return "no_item"
                inv_rowid, guest_muts = row['rowid'], row['mutations']
            await db.execute("DELETE FROM inventory WHERE rowid = ?", (inv_rowid,))
        await db.execute("UPDATE games SET guest_id = ?, guest_mutations = ?, status = 'playing' WHERE id = ?", (guest_pk, guest_muts, game_id))
        await db.commit()
        return "ok"

async def check_game_result(game_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM games WHERE id = ?", (game_id,)) as cur:
            game = await cur.fetchone()
        h_move, g_move = game['host_move'], game['guest_move']
        if not h_move or not g_move: return "waiting"
        winner_id = None
        if game['game_type'] == 'rps':
            if h_move == g_move: winner_id = 0
            elif (h_move=='rock' and g_move=='scissors') or (h_move=='scissors' and g_move=='paper') or (h_move=='paper' and g_move=='rock'): winner_id = game['host_id']
            else: winner_id = game['guest_id']
        elif game['game_type'] == 'even_odd':
            is_even = (int(h_move) % 2 == 0)
            if (is_even and g_move == 'even') or (not is_even and g_move == 'odd'): winner_id = game['guest_id']
            else: winner_id = game['host_id']
        if winner_id == 0:
            if game['wager_type'] == 'balance':
                await db.execute("UPDATE users SET balance = balance + ? WHERE id IN (?, ?)", (game['wager_amount'], game['host_id'], game['guest_id']))
            else:
                await db.execute("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?, ?, ?)", (game['host_id'], game['wager_item_id'], game['wager_mutations']))
                await db.execute("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?, ?, ?)", (game['guest_id'], game['wager_item_id'], game['guest_mutations']))
        else:
            if game['wager_type'] == 'balance':
                await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (game['wager_amount'] * 2, winner_id))
            else:
                await db.execute("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?, ?, ?)", (winner_id, game['wager_item_id'], game['wager_mutations']))
                await db.execute("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?, ?, ?)", (winner_id, game['wager_item_id'], game['guest_mutations']))
        await db.execute("UPDATE games SET status = 'finished', winner_id = ? WHERE id = ?", (winner_id, game_id))
        await db.commit()
        return "finished"

async def make_move(gid, uid_tg, move):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c:
            row = await c.fetchone()
            if not row: return "waiting"
            pk = row['id']
        async with db.execute("SELECT * FROM games WHERE id=?",(gid,)) as c: game=await c.fetchone()
        if pk==game['host_id']: await db.execute("UPDATE games SET host_move=? WHERE id=?",(move,gid))
        else: await db.execute("UPDATE games SET guest_move=? WHERE id=?",(move,gid))
        await db.commit()
    return await check_game_result(gid)

async def get_my_active_game(uid_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c:
            u_row = await c.fetchone()
            if not u_row: return None 
            pk = u_row['id']
        sql="""SELECT g.*, u1.username as host_name, u1.photo_url as host_photo, u2.username as guest_name, u2.photo_url as guest_photo, u1.tg_id as host_tg_id, u2.tg_id as guest_tg_id, i.name as item_name, i.image_url as item_img FROM games g LEFT JOIN users u1 ON g.host_id=u1.id LEFT JOIN users u2 ON g.guest_id=u2.id LEFT JOIN items i ON g.wager_item_id=i.id WHERE (g.host_id=? OR g.guest_id=?) AND g.status != 'finished' ORDER BY g.id DESC LIMIT 1"""
        async with db.execute(sql,(pk,pk)) as c: r=await c.fetchone(); return dict(r) if r else None

async def cancel_game_db(gid, uid_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c:
            row = await c.fetchone()
            if not row: return "err"
            pk = row['id']
        async with db.execute("SELECT * FROM games WHERE id=?",(gid,)) as c: game=await c.fetchone()
        if not game: return "err"
        if game['status']=='finished': await db.execute("DELETE FROM games WHERE id=?",(gid,)); await db.commit(); return "ok"
        if game['wager_type']=='balance': await db.execute("UPDATE users SET balance=balance+? WHERE id=?",(game['wager_amount'],pk))
        else: await db.execute("INSERT INTO inventory (user_id, item_id, mutations) VALUES (?,?,?)",(pk,game['wager_item_id'],game['wager_mutations']))
        await db.execute("DELETE FROM games WHERE id=?",(gid,)); await db.commit(); return "ok"

# --- ПРОЧЕЕ ---

async def get_all_cases():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases") as c: return await c.fetchall()
async def get_all_items_sorted():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM items ORDER BY price ASC") as c: return await c.fetchall()
async def get_case_data(cid):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases WHERE id=?",(cid,)) as c: return await c.fetchone()
async def get_case_items(cid):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM items WHERE case_id=?",(cid,)) as c: return await c.fetchall()
async def use_keys(uid_tg, cid, n):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c:
            row = await c.fetchone()
            if not row: return False
            pk = row[0]
        await db.execute("UPDATE keys SET quantity=quantity-? WHERE user_id=? AND case_id=?",(n,pk,cid))
        await db.commit()
        return True
async def get_user_keys(uid_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c:
            row = await c.fetchone()
            if not row: return {}
            pk = row['id']
        async with db.execute("SELECT case_id, quantity FROM keys WHERE user_id=? AND quantity>0",(pk,)) as c: return {r['case_id']:r['quantity'] for r in await c.fetchall()}
async def increment_cases_opened(uid_tg, n):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET cases_opened=cases_opened+? WHERE tg_id=?",(n,uid_tg)); await db.commit()
async def update_user_balance(uid_tg, n):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE tg_id=?",(n,uid_tg)); await db.commit()
async def update_user_ip(uid_tg, ip):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET ip=? WHERE tg_id=?",(ip,uid_tg)); await db.commit()
async def update_user_photo(uid_tg, url):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET photo_url=? WHERE tg_id=?",(url,uid_tg)); await db.commit()
async def get_rarity_weights():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT rarity, weight FROM rarity_weights") as c: return {r[0]:r[1] for r in await c.fetchall()}
async def sell_specific_item_stack(uid_tg, iid, muts, n, price):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c: pk=(await c.fetchone())[0]
        await db.execute("DELETE FROM inventory WHERE rowid IN (SELECT rowid FROM inventory WHERE user_id=? AND item_id=? AND mutations=? LIMIT ?)",(pk,iid,muts,n))
        if price>0: await db.execute("UPDATE users SET balance=balance+? WHERE id=?",(price,pk))
        await db.commit(); return True

async def get_public_profile(target_tg_id):
    user = await get_user(target_tg_id, "Unknown")
    if not user: return None
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        user_pk = user['id']
        sql_inv = """SELECT i.id as item_id, i.name, i.rarity, i.image_url, i.price, inv.mutations, COUNT(inv.item_id) as quantity FROM inventory AS inv JOIN items AS i ON inv.item_id = i.id WHERE inv.user_id = ? GROUP BY i.id, i.name, i.rarity, i.image_url, i.price, inv.mutations"""
        async with db.execute(sql_inv, (user_pk,)) as cur: inventory = [dict(row) for row in await cur.fetchall()]
        sql_sum = "SELECT SUM(i.price) FROM inventory inv JOIN items i ON inv.item_id = i.id WHERE inv.user_id = ?"
        async with db.execute(sql_sum, (user_pk,)) as cur: inv_val = (await cur.fetchone())[0] or 0
    
    best_item = await get_best_item_db(user['id'])
    
    user_dict = dict(user)
    user_dict['best_item'] = best_item
    user_dict['net_worth'] = user['balance'] + inv_val
    user_dict['inventory'] = inventory
    return user_dict

# Админ-функции
async def admin_get_user_inventory_detailed(uid_tg):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c: pk=(await c.fetchone())['id']
        sql="SELECT inv.rowid as unique_id, i.name, i.rarity, inv.mutations FROM inventory inv JOIN items i ON inv.item_id=i.id WHERE inv.user_id=?"
        async with db.execute(sql,(pk,)) as c: return [dict(r) for r in await c.fetchall()]
async def admin_update_inventory_mutation(rid, muts):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE inventory SET mutations=? WHERE rowid=?",(muts,rid)); await db.commit()
async def admin_update_field(tbl, rid, f, v):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE {tbl} SET {f}=? WHERE id=?",(v,rid)); await db.commit(); return True
async def add_keys_to_user(uid_tg, cid, n):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c: pk=(await c.fetchone())[0]
        await db.execute("INSERT INTO keys (user_id, case_id, quantity) VALUES (?,?,?) ON CONFLICT(user_id, case_id) DO UPDATE SET quantity=quantity+?",(pk,cid,n,n)); await db.commit()
async def add_specific_item_by_id(uid_tg, iid):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id FROM users WHERE tg_id=?",(uid_tg,)) as c: pk=(await c.fetchone())[0]
        await db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?,?)",(pk,iid)); await db.commit()
async def admin_add_case(n, p, u):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO cases (name, price, icon_url) VALUES (?,?,?)",(n,p,u)); await db.commit()
async def admin_del_case(cid):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM items WHERE case_id=?",(cid,)); await db.execute("DELETE FROM cases WHERE id=?",(cid,)); await db.commit()
async def admin_add_item(cid, n, r, p, u):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO items (name,rarity,price,image_url,sound_url,case_id) VALUES (?,?,?,?,?,?)",(n,r,p,u,'-',cid)); await db.commit()
async def admin_del_item(iid):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM items WHERE id=?",(iid,)); await db.commit()
async def get_item_by_id(iid):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM items WHERE id=?",(iid,)) as c: return await c.fetchone()
async def get_case_by_id(cid):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT * FROM cases WHERE id=?",(cid,)) as c: return await c.fetchone()