import asyncio
import requests
import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import API_KEY, BOT_TOKEN
from emojis import (CLOCK, SUN, CITY, THERMOMETER, DROPLET, WIND, CLOUD, 
                   WIND_BLOW, COMPASS, EYE, SUNRISE, SUNSET, CALENDAR, CLOUD_WITH_SUN)
from registration import Registration, init_db, add_user, get_user, is_registration_complete

# Координати для Полтави
LAT = 49.5937
LON = 34.5407
CITY_NAME = "Poltava"

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальна змінна для з’єднання з базою даних
conn = None

# Визначення станів для запуску бота
class UserState(StatesGroup):
    started = State()

# Функція для напрямку вітру
def wind_direction(degrees):
    directions = ["Північ", "Північний схід", "Схід", "Південний схід",
                  "Південь", "Південний захід", "Захід", "Північний захід"]
    index = round(degrees / 45) % 8
    return directions[index]

# Функція для поточної погоди
async def get_current_weather(user_name: str = None):
    url_current = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={API_KEY}&units=metric&lang=ua"
    response_current = requests.get(url_current)
    if response_current.status_code != 200:
        return f"Помилка: не вдалося отримати дані про погоду (код {response_current.status_code})."
    
    data_current = response_current.json()
    timezone_offset = data_current['timezone']
    sunrise_unix = data_current['sys']['sunrise']
    sunset_unix = data_current['sys']['sunset']
    sunrise_local = datetime.datetime.fromtimestamp(sunrise_unix)
    sunset_local = datetime.datetime.fromtimestamp(sunset_unix)
    pressure_hpa = data_current['main']['pressure']
    pressure_mmhg = pressure_hpa * 0.750062
    timezone_hours = data_current['timezone'] // 3600
    deg = data_current['wind']['deg']
    wind_dir = wind_direction(deg)

    greeting = f"Привіт, {user_name}!\n" if user_name else ""
    message = (
        f"{greeting}{SUN} *Прогноз на сьогодні (поточна погода)* {SUN}\n\n"
        f"{CITY} *Місто*: {CITY_NAME}\n"
        f"{THERMOMETER} *Температура*: {data_current['main']['temp']}°C\n"
        f"{THERMOMETER} *Відчувається як*: {data_current['main']['feels_like']}°C\n"
        f"{DROPLET} *Вологість*: {data_current['main']['humidity']}%\n"
        f"{WIND} *Тиск*: {pressure_mmhg:.2f} мм рт. ст.\n"
        f"{CLOUD} *Опис*: {data_current['weather'][0]['description']}\n"
        f"{WIND_BLOW} *Швидкість вітру*: {data_current['wind']['speed']} м/с\n"
        f"{WIND_BLOW} *Пориви*: {data_current['wind'].get('gust', 'немає даних')} м/с\n"
        f"{COMPASS} *Напрямок вітру*: {deg}° — {wind_dir}\n"
        f"{CLOUD} *Хмарність*: {data_current['clouds']['all']}%\n"
        f"{EYE} *Видимість*: {data_current['visibility']} м\n"
        f"{SUNRISE} *Схід сонця*: {sunrise_local.strftime('%H:%M')}\n"
        f"{SUNSET} *Захід сонця*: {sunset_local.strftime('%H:%M')}\n"
        f"{CLOCK} *Часовий пояс*: UTC{'+' if timezone_hours >= 0 else ''}{timezone_hours}"
    )
    return message

# Функція для прогнозу на завтра
async def get_tomorrow_weather():
    url_forecast = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=ua"
    response_forecast = requests.get(url_forecast)
    if response_forecast.status_code != 200:
        return f"Помилка: не вдалося отримати прогноз погоди (код {response_forecast.status_code})."
    
    data_forecast = response_forecast.json()
    tomorrow = datetime.datetime.now().date() + datetime.timedelta(days=1)
    message = f"{CLOUD_WITH_SUN} *Прогноз на завтра ({tomorrow})* {CLOUD_WITH_SUN}\n\n"
    
    found = False
    for forecast in data_forecast["list"]:
        time = datetime.datetime.fromtimestamp(forecast["dt"])
        if time.date() == tomorrow:
            found = True
            temp = forecast["main"]["temp"]
            desc = forecast["weather"][0]["description"]
            pressure_hpa = forecast["main"]["pressure"]
            pressure_mmhg = pressure_hpa * 0.750062
            deg = forecast["wind"]["deg"]
            wind_dir = wind_direction(deg)
            message += (
                f"{CLOCK} *Час*: {time.strftime('%H:%M')}\n"
                f"{THERMOMETER} *Температура*: {temp}°C\n"
                f"{CLOUD} *Опис*: {desc}\n"
                f"{WIND} *Тиск*: {pressure_mmhg:.2f} мм рт. ст.\n"
                f"{WIND_BLOW} *Швидкість вітру*: {forecast['wind']['speed']} м/с\n"
                f"{WIND_BLOW} *Пориви*: {forecast['wind'].get('gust', 'немає даних')} м/с\n"
                f"{COMPASS} *Напрямок вітру*: {deg}° — {wind_dir}\n"
                f"{CLOUD} *Хмарність*: {forecast['clouds']['all']}%\n"
                f"{EYE} *Видимість*: {forecast.get('visibility', 10000)} м\n"
                "---\n"
            )
    if not found:
        message += "Дані на завтра ще недоступні."
    return message

# Функція для прогнозу на кілька днів
async def get_multi_day_forecast():
    url_forecast = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&lang=ua"
    response_forecast = requests.get(url_forecast)
    if response_forecast.status_code != 200:
        return f"Помилка: не вдалося отримати прогноз погоди (код {response_forecast.status_code})."
    
    data_forecast = response_forecast.json()
    message = f"{CALENDAR} *Прогноз на кілька днів* {CALENDAR}\n\n"
    for forecast in data_forecast["list"]:
        time = datetime.datetime.fromtimestamp(forecast["dt"]).strftime('%Y-%m-%d %H:%M')
        temp = forecast["main"]["temp"]
        desc = forecast["weather"][0]["description"]
        message += f"{CLOCK} {time}: {temp}°C, {desc}\n"
    return message

# Інлайн-клавіатура для не зареєстрованих користувачів
def get_unregistered_inline_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Зареєструватися", callback_data="register")],
        [InlineKeyboardButton(text="Мій профіль", callback_data="profile")]
    ])
    return keyboard

# Інлайн-клавіатура для зареєстрованих користувачів
def get_registered_inline_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Прогноз на сьогодні", callback_data="today")],
        [InlineKeyboardButton(text="Прогноз на завтра", callback_data="tomorrow")],
        [InlineKeyboardButton(text="Прогноз на кілька днів", callback_data="multi_day")],
        [InlineKeyboardButton(text="Мій профіль", callback_data="profile")]
    ])
    return keyboard

# Обробник введення імені (переміщено перед handle_initial_message)
@dp.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    global conn
    user_id = message.from_user.id
    name = message.text.strip()
    current_state = await state.get_state()
    print(f"process_name triggered for user {user_id}, message: '{name}', state: {current_state}")
    if not name:
        await message.reply("Ім’я не може бути порожнім. Спробуйте ще раз:", parse_mode="Markdown")
        return
    user = await get_user(conn, user_id)
    if not user or not user["phone_number"]:
        print(f"Error: No phone number found for user {user_id}")
        await message.reply("Спочатку поділіться номером телефону через 'Зареєструватися'.",
                            reply_markup=get_unregistered_inline_keyboard(), parse_mode="Markdown")
        await state.clear()
        return
    await add_user(conn, user_id, phone_number=user["phone_number"], name=name)
    print(f"User {user_id} registered with phone: {user['phone_number']}, name: {name}")
    await message.reply(f"Реєстрацію завершено!\nНомер: {user['phone_number']}\nІм’я: {name}",
                        reply_markup=get_registered_inline_keyboard(), parse_mode="Markdown")
    await state.clear()
    print(f"State cleared for user {user_id}")

# Обробник першого повідомлення
@dp.message(lambda message: not message.contact)
async def handle_initial_message(message: Message, state: FSMContext):
    global conn
    user_id = message.from_user.id
    current_state = await state.get_state()
    
    print(f"User {user_id} sent message: '{message.text}', Current state: {current_state}")
    if current_state == "Registration:waiting_for_name":
        print(f"Skipping handle_initial_message for user {user_id} as state is waiting_for_name")
        return  # Пропускаємо обробку, якщо чекаємо ім’я
    if current_state is None:
        is_complete = await is_registration_complete(conn, user_id)
        print(f"User {user_id} initiated bot. Registration complete: {is_complete}")
        if is_complete:
            await message.reply("Вітаю! Виберіть опцію:", 
                              reply_markup=get_registered_inline_keyboard(), 
                              parse_mode="Markdown")
        else:
            user = await get_user(conn, user_id)
            if user and user["phone_number"] and not user["name"]:
                await message.reply("Ви вже поділилися номером телефону. Тепер введіть ваше ім’я:",
                                  parse_mode="Markdown")
                await state.set_state(Registration.waiting_for_name)
            else:
                await message.reply("Вітаю! Для доступу до прогнозів зареєструйтесь, поділившись номером телефону:",
                                  reply_markup=get_unregistered_inline_keyboard(), 
                                  parse_mode="Markdown")
        await state.set_state(UserState.started)
    else:
        user = await get_user(conn, user_id)
        if not await is_registration_complete(conn, user_id):
            if user and user["phone_number"] and not user["name"]:
                await message.reply("Ви вже поділилися номером телефону. Тепер введіть ваше ім’я:",
                                  parse_mode="Markdown")
                await state.set_state(Registration.waiting_for_name)
            else:
                await message.reply(f"{CLOCK} Для доступу до прогнозів зареєструйтесь, поділившись номером телефону:",
                                  reply_markup=get_unregistered_inline_keyboard(), 
                                  parse_mode="Markdown")
        else:
            await message.reply(f"{CLOCK} Оберіть опцію з меню:", 
                              reply_markup=get_registered_inline_keyboard(), 
                              parse_mode="Markdown")

# Обробник інлайн-кнопки "Зареєструватися"
@dp.callback_query(F.data == "register")
async def process_register_callback(callback: types.CallbackQuery, state: FSMContext):
    print(f"Callback 'register' triggered for user {callback.from_user.id}")
    await callback.message.reply("Поділіться номером телефону через кнопку нижче:",
                                 reply_markup=ReplyKeyboardMarkup(
                                     keyboard=[[KeyboardButton(text="Поділитися номером", request_contact=True)]],
                                     resize_keyboard=True
                                 ))
    await callback.answer()

# Обробник отримання номера телефону
@dp.message(F.contact)
async def process_phone(message: Message, state: FSMContext):
    global conn
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    print(f"User {user_id} shared phone: {phone_number}")
    await add_user(conn, user_id, phone_number=phone_number)
    await message.reply("Тепер введіть ваше ім’я:", parse_mode="Markdown")
    await state.set_state(Registration.waiting_for_name)
    print(f"State set to 'waiting_for_name' for user {user_id}")

# Обробник інлайн-кнопок
@dp.callback_query(F.data == "profile")
async def show_profile_inline(callback: types.CallbackQuery):
    global conn
    user_id = callback.from_user.id
    user = await get_user(conn, user_id)
    is_complete = await is_registration_complete(conn, user_id)
    print(f"User {user_id} requested profile. User data: {user}, Registration complete: {is_complete}")
    if user and is_complete:
        await callback.message.reply(f"Ваш профіль:\nНомер телефону: {user['phone_number']}\nІм’я: {user['name']}",
                                     reply_markup=get_registered_inline_keyboard(), parse_mode="Markdown")
    else:
        await callback.message.reply("Ви ще не завершили реєстрацію. Поділіться номером телефону через 'Зареєструватися'.",
                                     reply_markup=get_unregistered_inline_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "today")
async def handle_today_inline(callback: types.CallbackQuery):
    global conn
    user_id = callback.from_user.id
    is_complete = await is_registration_complete(conn, user_id)
    print(f"User {user_id} requested today weather. Registration complete: {is_complete}")
    if is_complete:
        user = await get_user(conn, user_id)
        weather = await get_current_weather(user["name"])
        await callback.message.reply(weather, reply_markup=get_registered_inline_keyboard(), parse_mode="Markdown")
    else:
        await callback.message.reply("Ви не зареєстровані. Поділіться номером телефону через 'Зареєструватися'.",
                                     reply_markup=get_unregistered_inline_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "tomorrow")
async def handle_tomorrow_inline(callback: types.CallbackQuery):
    global conn
    user_id = callback.from_user.id
    is_complete = await is_registration_complete(conn, user_id)
    print(f"User {user_id} requested tomorrow weather. Registration complete: {is_complete}")
    if is_complete:
        weather = await get_tomorrow_weather()
        if len(weather) > 4096:
            for i in range(0, len(weather), 4096):
                await callback.message.reply(weather[i:i+4096], reply_markup=get_registered_inline_keyboard(), parse_mode="Markdown")
        else:
            await callback.message.reply(weather, reply_markup=get_registered_inline_keyboard(), parse_mode="Markdown")
    else:
        await callback.message.reply("Ви не зареєстровані. Поділіться номером телефону через 'Зареєструватися'.",
                                     reply_markup=get_unregistered_inline_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "multi_day")
async def handle_multi_day_inline(callback: types.CallbackQuery):
    global conn
    user_id = callback.from_user.id
    is_complete = await is_registration_complete(conn, user_id)
    print(f"User {user_id} requested multi-day weather. Registration complete: {is_complete}")
    if is_complete:
        weather = await get_multi_day_forecast()
        if len(weather) > 4096:
            for i in range(0, len(weather), 4096):
                await callback.message.reply(weather[i:i+4096], reply_markup=get_registered_inline_keyboard(), parse_mode="Markdown")
        else:
            await callback.message.reply(weather, reply_markup=get_registered_inline_keyboard(), parse_mode="Markdown")
    else:
        await callback.message.reply("Ви не зареєстровані. Поділіться номером телефону через 'Зареєструватися'.",
                                     reply_markup=get_unregistered_inline_keyboard(), parse_mode="Markdown")
    await callback.answer()

# Запуск бота
async def main():
    global conn
    conn = await init_db()  # Ініціалізуємо з’єднання один раз
    try:
        await dp.start_polling(bot)
    finally:
        await conn.close()  # Закриваємо з’єднання після завершення

if __name__ == "__main__":
    asyncio.run(main())
#v2