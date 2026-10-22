import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict

import aiosqlite
from aiogram import BaseMiddleware, Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, TelegramObject
from google import genai

# ============ КОНФИГ ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ BOT_TOKEN или GEMINI_API_KEY не заданы!")

ADMIN_ID = 8777046904
ADMIN_USERNAME = "DietologLobar"

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'bot.db')

# Новый клиент Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-3.8-flash"

# ============ ПЕРЕВОДЫ ============
TEXTS = {
    "ru": {
        "choose_language": "🌐 Выберите язык / Tilni tanlang:",
        "welcome": "👋 Добро пожаловать! Я твой персональный ИИ-нутрициолог.\n\n✍️ Напиши, что ты съел (например: «Съел 200г курицы и гречку»), и я посчитаю калории и дам совет.\n\n📊 /today — итог за день\n💡 /advice — получить план питания и тренировок\n💳 /subscribe — оплата",
        "language_set": "✅ Язык: Русский",
        "payment_text": "💳 Оплата подписки: @DietologLobar\n\nПосле перевода нажмите кнопку ниже.",
        "pay_button": "Написать @DietologLobar",
        "paid_button": "✅ Я оплатил",
        "claim_sent": "Заявка отправлена. Ожидайте.",
        "sub_active": "🎉 Подписка активна до {date}",
        "need_sub": "⛔ Нужна подписка. /subscribe",
        "onboarding_gender": "👤 Ваш пол:",
        "onboarding_age": "🎂 Возраст (число):",
        "onboarding_weight": "⚖️ Вес в кг (например 75.5):",
        "onboarding_height": "📏 Рост в см (например 175):",
        "onboarding_activity": "🏃 Активность:",
        "onboarding_goal": "🎯 Цель:",
        "onboarding_done": "✅ Отлично! Норма: <b>{kcal} ккал/день</b>.\nТеперь просто пиши, что ты съел, а я буду считать и давать советы!",
        "gender_male": "👨 Мужской", "gender_female": "👩 Женский",
        "activity_low": "🪑 Сидячий", "activity_medium": "🚶 Средний", "activity_high": "🏋️ Высокий",
        "goal_lose": "📉 Похудеть", "goal_keep": "⚖️ Удержать",
        "analyzing": "🔍 Считаю калории и анализирую...",
        "food_result": "🍽 <b>{dish}</b>\n🔥 {calories} ккал (Б:{proteins} Ж:{fats} У:{carbs})\n\n📊 Съедено сегодня: {today}/{norm} ккал\n\n💡 <b>Совет:</b> {advice}",
        "advice_loading": "🧠 Составляю персональный план на основе твоих данных...",
        "advice_result": "💡 <b>Твой персональный план:</b>\n\n{text}",
        "today_empty": "📭 Сегодня ты ещё ничего не записал. Просто напиши, что съел!",
        "today_header": "📊 <b>Сегодня</b>\n",
        "today_item": "• {name}: {cal} ккал\n",
        "today_footer": "\n🔥 Итого: <b>{total}/{norm}</b>",
        "no_norm": "⚠️ Сначала пройди опрос: /start",
        "blocked": "⛔ Вы заблокированы.",
        "error_generic": "⚠️ Ошибка ИИ. Попробуйте позже.",
        "error_quota": "⚠️ Слишком много запросов. Подождите минуту.",
    },
    "uz": {
        "choose_language": "🌐 Выберите язык / Tilni tanlang:",
        "welcome": "👋 Xush kelibsiz! Men sizning shaxsiy AI-dietologingizman.\n\n✍️ Nima yeganingizni yozing (masalan: «200g tovuq va grechka»), men kaloriya hisoblab, maslahat beraman.\n\n📊 /today — bugungi natija\n💡 /advice — ovqatlanish va mashq rejasi\n💳 /subscribe — to'lov",
        "language_set": "✅ Til: O'zbekcha",
        "payment_text": "💳 To'lov: @DietologLobar\n\nTo'lovdan so'ng tugmani bosing.",
        "pay_button": "@DietologLobar ga yozish",
        "paid_button": "✅ Men to'ladim",
        "claim_sent": "So'rov yuborildi. Kuting.",
        "sub_active": "🎉 Obuna {date} gacha faol",
        "need_sub": "⛔ Obuna kerak. /subscribe",
        "onboarding_gender": "👤 Jinsingiz:",
        "onboarding_age": "🎂 Yosh (raqam):",
        "onboarding_weight": "⚖️ Vazn kg (masalan 75.5):",
        "onboarding_height": "📏 Bo'y sm (masalan 175):",
        "onboarding_activity": "🏃 Faollik:",
        "onboarding_goal": "🎯 Maqsad:",
        "onboarding_done": "✅ Ajoyib! Norma: <b>{kcal} kkal/kun</b>.\nEndi nima yeganingizni yozing, men hisoblayman va maslahat beraman!",
        "gender_male": "👨 Erkak", "gender_female": "👩 Ayol",
        "activity_low": "🪑 Kam", "activity_medium": "🚶 O'rtacha", "activity_high": "🏋️ Yuqori",
        "goal_lose": "📉 Ozish", "goal_keep": "⚖️ Saqlash",
        "analyzing": "🔍 Kaloriya hisoblanmoqda va tahlil qilinmoqda...",
        "food_result": "🍽 <b>{dish}</b>\n🔥 {calories} kkal (O:{proteins} Y:{fats} U:{carbs})\n\n📊 Bugun yeyilgan: {today}/{norm} kkal\n\n💡 <b>Maslahat:</b> {advice}",
        "advice_loading": "🧠 Ma'lumotlaringiz asosida shaxsiy reja tuzilmoqda...",
        "advice_result": "💡 <b>Sizning shaxsiy rejangiz:</b>\n\n{text}",
        "today_empty": "📭 Bugun hali hech narsa yozmadingiz. Nima yeganingizni yozing!",
        "today_header": "📊 <b>Bugun</b>\n",
        "today_item": "• {name}: {cal} kkal\n",
        "today_footer": "\n🔥 Jami: <b>{total}/{norm}</b>",
        "no_norm": "⚠️ Avval so'rovnomani o'ting: /start",
        "blocked": "⛔ Siz bloklangansiz.",
        "error_generic": "⚠️ AI xatosi. Keyinroq urinib ko'ring.",
        "error_quota": "⚠️ Juda ko'p so'rov. Bir daqiqa kuting.",
    },
}

def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, "")
    return text.format(**kwargs) if kwargs else text

# ============ БД ============
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, language TEXT,
            subscription_end TEXT, is_blocked INTEGER DEFAULT 0,
            gender TEXT, age INTEGER, weight REAL, height REAL,
            activity TEXT, goal TEXT, daily_kcal INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT,
            food_name TEXT, calories INTEGER, proteins REAL, fats REAL, carbs REAL)""")
        await db.commit()

async def register_user(user_id: int, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, language, subscription_end, is_blocked) VALUES (?, ?, NULL, NULL, 0)",
            (user_id, username))
        await db.commit()

async def get_raw_lang(user_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else None

async def get_user_lang(user_id: int) -> str:
    return await get_raw_lang(user_id) or "ru"

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()

async def is_subscribed(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    if not row or not row[0]: return False
    return datetime.fromisoformat(row[0]) > datetime.now()

async def activate_subscription(user_id: int, days: int) -> datetime:
    end_date = datetime.now() + timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (end_date.isoformat(), user_id))
        await db.commit()
    return end_date

async def extend_subscription(user_id: int, days: int) -> datetime | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row: return None
        now = datetime.now()
        current_end = datetime.fromisoformat(row[0]) if row[0] else None
        base = current_end if current_end and current_end > now else now
        new_end = base + timedelta(days=days)
        await db.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end.isoformat(), user_id))
        await db.commit()
        return new_end

async def set_blocked(user_id: int, blocked: bool) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (1 if blocked else 0, user_id))
        await db.commit()
        return cur.rowcount > 0

async def is_blocked(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    return bool(row and row[0])

async def get_user_profile(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None

async def update_user_profile(user_id: int, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()

async def save_meal(user_id: int, food_name: str, calories: int, proteins: float, fats: float, carbs: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO meals (user_id, date, food_name, calories, proteins, fats, carbs) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, datetime.now().date().isoformat(), food_name, calories, proteins, fats, carbs))
        await db.commit()

async def get_today_meals(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM meals WHERE user_id = ? AND date = ?", (user_id, datetime.now().date().isoformat())) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]

async def get_today_total(user_id: int) -> int:
    return sum(m["calories"] for m in await get_today_meals(user_id))

# ============ MIDDLEWARE ============
class BlockCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and user.id != ADMIN_ID and await is_blocked(user.id):
            lang = await get_user_lang(user.id)
            msg = t(lang, "blocked")
            if isinstance(event, Message): await event.answer(msg)
            elif isinstance(event, CallbackQuery): await event.answer(msg, show_alert=True)
            return
        return await handler(event, data)

# ============ БЕЗОПАСНЫЙ ВЫЗОВ GEMINI (ИСПРАВЛЕНО) ============
async def safe_gemini_call(prompt: str):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # ИСПОЛЬЗУЕМ INTERACTIONS API ДЛЯ GEMINI 3
            interaction = await asyncio.to_thread(
                client.interactions.create,
                model=MODEL_ID,
                input=prompt
            )
            return interaction.output_text.strip()
        except Exception as e:
            error_str = str(e).lower()
            logging.error(f"Gemini attempt {attempt+1} failed: {e}")
            if "429" in error_str or "quota" in error_str or "resource exhausted" in error_str:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise Exception("QUOTA_EXCEEDED")
            raise e

# ============ КЛАВИАТУРЫ ============
def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"), InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")]])

def payment_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "pay_button"), url=f"https://t.me/{ADMIN_USERNAME}")],[InlineKeyboardButton(text=t(lang, "paid_button"), callback_data="user_paid_claim")]])

def gender_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "gender_male"), callback_data="ob_male"), InlineKeyboardButton(text=t(lang, "gender_female"), callback_data="ob_female")]])

def activity_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "activity_low"), callback_data="ob_low")], [InlineKeyboardButton(text=t(lang, "activity_medium"), callback_data="ob_medium")], [InlineKeyboardButton(text=t(lang, "activity_high"), callback_data="ob_high")]])

def goal_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "goal_lose"), callback_data="ob_lose")], [InlineKeyboardButton(text=t(lang, "goal_keep"), callback_data="ob_keep")]])

# ============ РОУТЕР ============
router = Router()
onboarding_state: Dict[int, dict] = {}

@router.message(CommandStart())
async def cmd_start(message: Message):
    await register_user(message.from_user.id, message.from_user.username)
    raw_lang = await get_raw_lang(message.from_user.id)
    if raw_lang:
        profile = await get_user_profile(message.from_user.id)
        if not profile or not profile.get("daily_kcal"): await start_onboarding(message, raw_lang)
        else: await message.answer(t(raw_lang, "welcome"))
    else:
        await message.answer("🌐 Выберите язык / Tilni tanlang:", reply_markup=language_keyboard())

@router.callback_query(F.data.in_({"lang_ru", "lang_uz"}))
async def set_language(callback: CallbackQuery):
    lang = "ru" if callback.data == "lang_ru" else "uz"
    await set_user_lang(callback.from_user.id, lang)
    await callback.message.edit_text(t(lang, "language_set"))
    profile = await get_user_profile(callback.from_user.id)
    if not profile or not profile.get("daily_kcal"): await start_onboarding(callback.message, lang)
    else: await callback.message.answer(t(lang, "welcome"))
    await callback.answer()

async def start_onboarding(message: Message, lang: str):
    onboarding_state[message.chat.id] = {"step": "gender"}
    await message.answer(t(lang, "onboarding_gender"), reply_markup=gender_keyboard(lang))

@router.callback_query(F.data.startswith("ob_"))
async def onboarding_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_user_lang(user_id)
    data = callback.data
    if data in ("ob_male", "ob_female"):
        onboarding_state[user_id] = {"step": "age", "gender": "male" if data == "ob_male" else "female"}
        await callback.message.answer(t(lang, "onboarding_age"))
    elif data in ("ob_low", "ob_medium", "ob_high"):
        onboarding_state[user_id]["activity"] = data.replace("ob_", "")
        onboarding_state[user_id]["step"] = "goal"
        await callback.message.answer(t(lang, "onboarding_goal"), reply_markup=goal_keyboard(lang))
    elif data in ("ob_lose", "ob_keep"):
        onboarding_state[user_id]["goal"] = data.replace("ob_", "")
        await finish_onboarding(callback.message, user_id, lang, onboarding_state[user_id])
    await callback.answer()

@router.message(F.text.regexp(r"^\d+([.,]\d+)?$"))
async def onboarding_numbers(message: Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    state = onboarding_state.get(user_id)
    if not state: return
    try: value = float(message.text.replace(",", "."))
    except ValueError: return
    step = state.get("step")
    if step == "age":
        state["age"] = int(value); state["step"] = "weight"
        await message.answer(t(lang, "onboarding_weight"))
    elif step == "weight":
        state["weight"] = value; state["step"] = "height"
        await message.answer(t(lang, "onboarding_height"))
    elif step == "height":
        state["height"] = value; state["step"] = "activity"
        await message.answer(t(lang, "onboarding_activity"), reply_markup=activity_keyboard(lang))

async def finish_onboarding(message: Message, user_id: int, lang: str, state: dict):
    gender, age, weight, height = state.get("gender", "male"), state.get("age", 30), state.get("weight", 70), state.get("height", 170)
    activity, goal = state.get("activity", "low"), state.get("goal", "lose")
    bmr = (10 * weight + 6.25 * height - 5 * age + 5) if gender == "male" else (10 * weight + 6.25 * height - 5 * age - 161)
    tdee = bmr * {"low": 1.2, "medium": 1.55, "high": 1.725}.get(activity, 1.2)
    daily_kcal = int(tdee - 500) if goal == "lose" else int(tdee)
    await update_user_profile(user_id, gender=gender, age=age, weight=weight, height=height, activity=activity, goal=goal, daily_kcal=daily_kcal)
    onboarding_state.pop(user_id, None)
    await message.answer(t(lang, "onboarding_done", kcal=daily_kcal))

@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "payment_text"), reply_markup=payment_keyboard(lang))

@router.callback_query(F.data == "user_paid_claim")
async def claim_payment(callback: CallbackQuery):
    user = callback.from_user
    lang = await get_user_lang(user.id)
    await callback.bot.send_message(ADMIN_ID, f"💰 Заявка: {user.full_name} (@{user.username})\nID: <code>{user.id}</code>\n/activate {user.id} 30")
    await callback.message.answer(t(lang, "claim_sent"))
    await callback.answer()

# ============ ЛОГИКА ПИТАНИЯ ============
@router.message(F.text & ~F.text.startswith("/"))
async def handle_food_text(message: Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    
    if not await is_subscribed(user_id): return await message.answer(t(lang, "need_sub"))
    profile = await get_user_profile(user_id)
    if not profile or not profile.get("daily_kcal"): return await message.answer(t(lang, "no_norm"))

    msg = await message.answer(t(lang, "analyzing"))
    
    prompt = f"""Ты профессиональный нутрициолог. Пользователь съел: "{message.text}".
Его данные: Пол: {profile['gender']}, Возраст: {profile['age']}, Вес: {profile['weight']}кг, Рост: {profile['height']}см, Цель: {profile['goal']}.
Его дневная норма: {profile['daily_kcal']} ккал. Сегодня он уже съел: {await get_today_total(user_id)} ккал.

Оцени съеденное. Верни ответ СТРОГО в формате JSON (без markdown):
{{
  "dish": "краткое название блюда",
  "calories": 450,
  "proteins": 30.5,
  "fats": 15.0,
  "carbs": 40.0,
  "advice": "Короткий совет (1-2 предложения) на основе его цели и того, что он съел."
}}"""

    try:
        raw_text = await safe_gemini_call(prompt)
        
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"): raw_text = raw_text[4:]
        start, end = raw_text.find("{"), raw_text.rfind("}") + 1
        if start != -1 and end != 0: raw_text = raw_text[start:end]

        data = json.loads(raw_text)
        
        dish = data.get("dish", message.text[:50])
        calories = int(data.get("calories", 0))
        proteins = float(data.get("proteins", 0))
        fats = float(data.get("fats", 0))
        carbs = float(data.get("carbs", 0))
        advice = data.get("advice", "Хорошего дня!")

        await save_meal(user_id, dish, calories, proteins, fats, carbs)
        today_total = await get_today_total(user_id)

        await msg.edit_text(t(lang, "food_result", 
            dish=dish, calories=calories, proteins=proteins, fats=fats, carbs=carbs,
            today=today_total, norm=profile["daily_kcal"], advice=advice
        ))
    except Exception as e:
        logging.error(f"Food error: {e}")
        await msg.edit_text(t(lang, "error_quota") if "QUOTA" in str(e) else t(lang, "error_generic"))

@router.message(Command("advice"))
async def cmd_advice(message: Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    
    if not await is_subscribed(user_id): return await message.answer(t(lang, "need_sub"))
    profile = await get_user_profile(user_id)
    if not profile or not profile.get("daily_kcal"): return await message.answer(t(lang, "no_norm"))

    msg = await message.answer(t(lang, "advice_loading"))
    
    prompt = f"""Ты профессиональный фитнес-тренер и нутрициолог. Составь подробный план на день для пользователя.
Данные: Пол: {profile['gender']}, Возраст: {profile['age']}, Вес: {profile['weight']}кг, Рост: {profile['height']}см, Активность: {profile['activity']}, Цель: {profile['goal']}.
Норма калорий: {profile['daily_kcal']} ккал.

Напиши ответ в виде красивого текста (используй эмодзи и переносы строк), раздели на блоки:
1. 🍳 План питания (что и когда есть, чтобы вписаться в норму).
2. 🏋️ План тренировок (какие упражнения делать дома без инвентаря).
3. 💡 Лайфхак дня.

Пиши кратко, мотивирующе и по делу."""

    try:
        advice_text = await safe_gemini_call(prompt)
        await msg.edit_text(t(lang, "advice_result", text=advice_text))
    except Exception as e:
        logging.error(f"Advice error: {e}")
        await msg.edit_text(t(lang, "error_quota") if "QUOTA" in str(e) else t(lang, "error_generic"))

@router.message(Command("today"))
async def cmd_today(message: Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    if not await is_subscribed(user_id): return await message.answer(t(lang, "need_sub"))
    profile = await get_user_profile(user_id)
    meals = await get_today_meals(user_id)
    if not meals: return await message.answer(t(lang, "today_empty"))
    text = t(lang, "today_header")
    total = 0
    for m in meals:
        text += t(lang, "today_item", name=m["food_name"], cal=m["calories"])
        total += m["calories"]
    text += t(lang, "today_footer", total=total, norm=profile["daily_kcal"])
    await message.answer(text)

# ============ АДМИН ============
@router.message(Command("activate"))
async def activate_sub(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 3: return await message.answer("Использование: /activate <id> <days>")
    try: target_id, days = int(args[1]), int(args[2])
    except ValueError: return await message.answer("❌ Ошибка в числах.")
    end_date = await activate_subscription(target_id, days)
    await message.answer(f"✅ {target_id} активирован до {end_date.date()}")
    try: await message.bot.send_message(target_id, t(await get_user_lang(target_id), "sub_active", date=end_date.date()))
    except Exception: pass

@router.message(Command("extend"))
async def cmd_extend(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 3: return await message.answer("Использование: /extend <id> <days>")
    try: target_id, days = int(args[1]), int(args[2])
    except ValueError: return await message.answer("❌ Ошибка в числах.")
    new_end = await extend_subscription(target_id, days)
    if new_end is None: return await message.answer("❌ Пользователь не найден.")
    await message.answer(f"✅ {target_id} продлен на {days} дн. до {new_end.date()}")
    try: await message.bot.send_message(target_id, t(await get_user_lang(target_id), "extend_notify", days=days, date=new_end.date()))
    except Exception: pass

@router.message(Command("check"))
async def check_sub(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 2: return await message.answer("Использование: /check <id>")
    try: target_id = int(args[1])
    except ValueError: return await message.answer("❌ id должен быть числом.")
    status = "✅ активна" if await is_subscribed(target_id) else "⛔ не активна"
    blocked = "🚫 заблокирован" if await is_blocked(target_id) else "🟢 не заблокирован"
    await message.answer(f"Пользователь {target_id}:\nПодписка: {status}\nСтатус: {blocked}")

@router.message(Command("block"))
async def cmd_block(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 2: return await message.answer("Использование: /block <id>")
    try: target_id = int(args[1])
    except ValueError: return await message.answer("❌ id должен быть числом.")
    if not await set_blocked(target_id, True): return await message.answer("❌ Не найден.")
    await message.answer(f"🚫 {target_id} заблокирован.")

@router.message(Command("unblock"))
async def cmd_unblock(message: Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) != 2: return await message.answer("Использование: /unblock <id>")
    try: target_id = int(args[1])
    except ValueError: return await message.answer("❌ id должен быть числом.")
    if not await set_blocked(target_id, False): return await message.answer("❌ Не найден.")
    await message.answer(f"✅ {target_id} разблокирован.")

# ============ MAIN ============
async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.middleware(BlockCheckMiddleware())
    dp.callback_query.middleware(BlockCheckMiddleware())
    dp.include_router(router)
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
