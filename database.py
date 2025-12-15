import aiosqlite
import sqlite3

DB_NAME = "brainrot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row 
        
        # Создаем таблицы
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, balance INTEGER DEFAULT 1000)")
        await db.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY, name TEXT UNIQUE, price INTEGER, icon_url TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, rarity TEXT, price INTEGER, image_url TEXT, sound_url TEXT, case_id INTEGER, FOREIGN KEY (case_id) REFERENCES cases(id))")
        await db.execute("CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, user_id INTEGER, item_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES items(id))")
        
        await db.commit()
        
        # --- НАПОЛНЕНИЕ КОНТЕНТОМ ---
        
        # 1. Создаем КЕЙСЫ
        cases_data = [
            ('📦 Bicara Case', 100, 'https://cdn-icons-png.flaticon.com/512/11560/11560682.png'),
            ('🗿 Sigma Case', 500, 'https://cdn-icons-png.flaticon.com/512/12222/12222838.png'),
            ('🚽 Skibidi Case', 1500, 'https://cdn-icons-png.flaticon.com/512/12406/12406859.png')
        ]
        
        for name, price, icon in cases_data:
            await db.execute("INSERT OR IGNORE INTO cases (name, price, icon_url) VALUES (?, ?, ?)", (name, price, icon))
        
        await db.commit()

        # Получаем ID кейсов
        c1 = (await db.execute("SELECT id FROM cases WHERE name = '📦 Bicara Case'")).fetchone_await()
        c2 = (await db.execute("SELECT id FROM cases WHERE name = '🗿 Sigma Case'")).fetchone_await()
        c3 = (await db.execute("SELECT id FROM cases WHERE name = '🚽 Skibidi Case'")).fetchone_await()
        
        # Исправление для aiosqlite (если fetchone_await не сработал бы, но тут мы используем await cursor)
        # Упростим получение ID для надежности:
        async with db.execute("SELECT id FROM cases WHERE name = '📦 Bicara Case'") as cur: c1_id = (await cur.fetchone())[0]
        async with db.execute("SELECT id FROM cases WHERE name = '🗿 Sigma Case'") as cur: c2_id = (await cur.fetchone())[0]
        async with db.execute("SELECT id FROM cases WHERE name = '🚽 Skibidi Case'") as cur: c3_id = (await cur.fetchone())[0]

        # 2. Создаем ПРЕДМЕТЫ (Бреинроты)
        # Формат: (Название, Редкость, Цена, Картинка, Звук, ID_Кейса)
        items_data = [
            # Bicara Case (Дешевые мемы)
            ('Sad Hamster', 'Common', 50, 'https://i.pinimg.com/736x/8a/92/97/8a92973163773ba393a6703b413c604d.jpg', '-', c1_id),
            ('Nerd Emoji', 'Common', 60, 'https://cdn-icons-png.flaticon.com/512/9681/9681329.png', '-', c1_id),
            ('Pedro Raccoon', 'Uncommon', 150, 'https://media1.tenor.com/m/K7c0j3q5aE8AAAAC/raccoon-pedro.gif', '-', c1_id),
            ('Chinese Cat', 'Uncommon', 180, 'https://i.pinimg.com/736x/55/88/47/55884766023246473857e4922154446a.jpg', '-', c1_id),
            ('Bicara Boy', 'Rare', 500, 'https://i.imgur.com/example_bicara.png', '-', c1_id),

            # Sigma Case (Крутые)
            ('Mewing Guy', 'Common', 300, 'https://i1.sndcdn.com/artworks-5wJ49g2GgH2K8z1e-0k8p2Q-t500x500.jpg', '-', c2_id),
            ('Patrick Bateman', 'Uncommon', 600, 'https://i.pinimg.com/originals/a0/02/89/a002890538a83ce40875e5387431e78c.jpg', '-', c2_id),
            ('Gigachad', 'Rare', 1200, 'https://cdn-icons-png.flaticon.com/512/11560/11560682.png', '-', c2_id),
            ('Ryan Gosling', 'Rare', 1500, 'https://i.pinimg.com/736x/ea/5e/54/ea5e546112953258c7e6c40683a37b38.jpg', '-', c2_id),
            ('Tyler Durden', 'Mythical', 5000, 'https://i.pinimg.com/736x/f6/e1/99/f6e19999056d686004b5003318255476.jpg', '-', c2_id),

            # Skibidi Case (Самый жир)
            ('Toilet Mini', 'Common', 800, 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Toilet_icon.svg/1200px-Toilet_icon.svg.png', '-', c3_id),
            ('Cameraman', 'Uncommon', 1500, 'https://static.wikia.nocookie.net/skibidi-toilet-official/images/7/75/Cameraman_infobox.png', '-', c3_id),
            ('Grimace Shake', 'Rare', 3000, 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Grimace_Shake.png/640px-Grimace_Shake.png', '-', c3_id),
            ('G-Man Toilet', 'Mythical', 10000, 'https://static.wikia.nocookie.net/skibidi-toilet-official/images/e/e4/G-Man_Skibidi_Toilet_infobox.png', '-', c3_id),
            ('Titan Speakerman', 'Mythical', 25000, 'https://static.wikia.nocookie.net/skibidi-toilet-official/images/2/22/TitanSpeakerman_infobox.png', '-', c3_id)
        ]

        for i in items_data:
            # Проверяем по имени, чтобы не дублировать
            async with db.execute("SELECT id FROM items WHERE name = ?", (i[0],)) as cur:
                if not await cur.fetchone():
                    await db.execute("INSERT INTO items (name, rarity, price, image_url, sound_url, case_id) VALUES (?, ?, ?, ?, ?, ?)", i)

        await db.commit()

# --- ОСНОВНЫЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ, НО ВСТАВЬ ИХ СЮДА) ---

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
        sql = "SELECT inv.id as inv_id, i.id as item_id, i.name, i.rarity, i.image_url, i.price FROM inventory AS inv JOIN items AS i ON inv.item_id = i.id WHERE inv.user_id = ?"
        async with db.execute(sql, (user_id,)) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def sell_item_db(user_id, inv_id, price):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM inventory WHERE id = ? AND user_id = ?", (inv_id, user_id))
        await db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (price, user_id))
        await db.commit()

async def get_leaderboard():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = sqlite3.Row
        async with db.execute("SELECT username, balance FROM users WHERE tg_id != 0 ORDER BY balance DESC LIMIT 10") as cursor:
            return [dict(row) for row in await cursor.fetchall()]

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
        query = f"UPDATE items SET {field} = ? WHERE id = ?"
        await db.execute(query, (value, item_id))
        await db.commit()