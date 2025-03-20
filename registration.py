import asyncpg
from aiogram.fsm.state import State, StatesGroup
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

# Визначення станів для реєстрації
class Registration(StatesGroup):
    waiting_for_phone = State()  # Очікування номера телефону
    waiting_for_name = State()   # Очікування імені

# Ініціалізація бази даних
async def init_db():
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST
    )
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            phone_number TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL DEFAULT ''
        )
    """)
    # Додаємо стовпець phone_number, якщо його ще немає
    #await conn.execute("""
    #    ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number TEXT NOT NULL DEFAULT ''
    #""")
    await conn.close()

# Додавання користувача
async def add_user(user_id: int, phone_number: str = None, name: str = None):
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST
    )
    if phone_number and name:
        await conn.execute(
            "INSERT INTO users (user_id, phone_number, name) VALUES ($1, $2, $3) "
            "ON CONFLICT (user_id) DO UPDATE SET phone_number = $2, name = $3",
            user_id, phone_number, name
        )
    elif phone_number:
        await conn.execute(
            "INSERT INTO users (user_id, phone_number, name) VALUES ($1, $2, '') "
            "ON CONFLICT (user_id) DO UPDATE SET phone_number = $2",
            user_id, phone_number
        )
    elif name:
        await conn.execute(
            "INSERT INTO users (user_id, phone_number, name) VALUES ($1, '', $2) "
            "ON CONFLICT (user_id) DO UPDATE SET name = $2",
            user_id, name
        )
    await conn.close()

# Отримання користувача
async def get_user(user_id: int):
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST
    )
    result = await conn.fetchrow("SELECT phone_number, name FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return {"phone_number": result["phone_number"], "name": result["name"]} if result else None

# Перевірка завершення реєстрації
async def is_registration_complete(user_id: int):
    user = await get_user(user_id)
    return user is not None and bool(user.get("phone_number")) and bool(user.get("name"))
    #print(f"Checking registration for user {user_id}: {user}")  # Дебаг-вивід
    #return user is not None and user["phone_number"] and user["name"]