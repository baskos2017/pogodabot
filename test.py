import asyncio
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import BOT_TOKEN, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME  # Додайте параметри в config.py

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Визначення станів
class Registration(StatesGroup):
    waiting_for_name = State()

# Підключення до бази даних
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
            name TEXT NOT NULL
        )
    """)
    await conn.close()

# Функція для додавання користувача
async def add_user(user_id: int, name: str):
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST
    )
    await conn.execute(
        "INSERT INTO users (user_id, name) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET name = $2",
        user_id, name
    )
    await conn.close()

# Функція для отримання користувача
async def get_user(user_id: int):
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST
    )
    result = await conn.fetchrow("SELECT name FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return {"name": result["name"]} if result else None

# Створення клавіатури
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Зареєструватися")],
            [KeyboardButton(text="Мій профіль")],
        ],
        resize_keyboard=True
    )
    return keyboard

# Обробник /start
@dp.message(Command("start"))
async def send_welcome(message: Message, state: FSMContext):
    await message.reply("Привіт! Я бот з реєстрацією. Виберіть опцію:", reply_markup=get_main_keyboard())
    await state.clear()

# Обробник "Зареєструватися"
@dp.message(F.text == "Зареєструватися")
async def start_registration(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user:
        await message.reply("Ви вже зареєстровані! Перегляньте профіль у 'Мій профіль'.")
    else:
        await message.reply("Введіть ваше ім’я для реєстрації:")
        await state.set_state(Registration.waiting_for_name)

# Обробник введення імені
@dp.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    if not name:
        await message.reply("Ім’я не може бути порожнім. Спробуйте ще раз:")
        return
    await add_user(user_id, name)
    await message.reply(f"Реєстрацію завершено! Ваше ім’я: {name}", reply_markup=get_main_keyboard())
    await state.clear()

# Обробник "Мій профіль"
@dp.message(F.text == "Мій профіль")
async def show_profile(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user:
        await message.reply(f"Ваш профіль:\nІм’я: {user['name']}")
    else:
        await message.reply("Ви ще не зареєстровані. Натисніть 'Зареєструватися'.")

# Обробник невідомих повідомлень
@dp.message()
async def handle_unknown(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.reply("Введіть /start, щоб запустити бота.")
    else:
        await message.reply("Оберіть опцію з меню або завершіть реєстрацію.")

# Запуск бота
async def main():
    await init_db()  # Ініціалізація бази даних
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())