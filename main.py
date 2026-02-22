import asyncio
import logging
import json
import os
import math
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
TOKEN = "7714657648:AAH1zEV5p2gHHowtYnKHkMnIYX88UirHeGs"
ADMIN_ID = 123456789  # ЗАМЕНИ НА СВОЙ ID (чтобы работала рассылка)
DB_FILE = "gift_db.json"
PERCENT_FEE = 0.15
REFERRAL_REWARD = 5   # Сколько Stars даем за друга

# Витрина (ID подарка: [Название, Цена])
SHOP_ITEMS = {
    "220": ["Rare Blue Star", 50],
    "350": ["Vintage Heart", 75],
    "500": ["Golden Rocket", 150]
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_user(db, user_id, referrer=None):
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "balance": 0,
            "referred_by": referrer,
            "referrals_count": 0,
            "history": []
        }
        if referrer and str(referrer) in db:
            db[str(referrer)]["referrals_count"] += 1
    return db

# --- КОМАНДЫ ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="shop", description="Витрина подарков"),
        BotCommand(command="balance", description="Кошелек"),
        BotCommand(command="ref", description="Рефералы"),
        BotCommand(command="history", description="Мои подарки"),
        BotCommand(command="help", description="Помощь")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Логика реферала: /start 1234567
    args = message.text.split()
    referrer = args[1] if len(args) > 1 and args[1].isdigit() else None
    
    db = load_db()
    db = init_user(db, message.from_user.id, referrer)
    save_db(db)
    
    await message.answer(
        "✨ **Добро пожаловать в GiftExcuse!**\n\n"
        "Мы — твой доступ к архивным подаркам Telegram API.\n"
        "Выбирай подарок в /shop или отправляй по ID.",
        parse_mode="Markdown"
    )

@dp.message(Command("shop"))
async def cmd_shop(message: types.Message):
    builder = InlineKeyboardBuilder()
    for item_id, info in SHOP_ITEMS.items():
        builder.row(InlineKeyboardButton(
            text=f"🎁 {info[0]} — {info[1]} ⭐", 
            callback_data=f"buy_{item_id}")
        )
    await message.answer("🛒 **Витрина редких подарков:**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message(Command("ref"))
async def cmd_ref(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    user_data = db.get(uid, {"referrals_count": 0})
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={uid}"
    
    await message.answer(
        f"👥 **Партнерская программа**\n\n"
        f"Приглашено друзей: {user_data['referrals_count']}\n"
        f"Награда за каждого друга: {REFERRAL_REWARD} ⭐ (после его пополнения)\n\n"
        f"Твоя ссылка:\n`{ref_link}`",
        parse_mode="Markdown"
    )

@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    db = load_db()
    history = db.get(str(message.from_user.id), {}).get("history", [])
    if not history:
        return await message.answer("История отправлений пуста.")
    
    text = "📜 **Последние подарки:**\n" + "\n".join(history[-10:])
    await message.answer(text, parse_mode="Markdown")

# --- ОПЛАТА ---
@dp.message(Command("topup"))
async def cmd_topup(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("Используй: `/topup 100`", parse_mode="Markdown")
    
    amount = int(parts[1])
    total = amount + math.ceil(amount * PERCENT_FEE)
    
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Пополнение баланса",
        description=f"Зачисление {amount} Stars",
        payload=f"topup_{amount}",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=total)]
    )

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    amount = int(message.successful_payment.invoice_payload.split("_")[1])
    
    # Начисление бонуса пригласившему (единоразово при первом пополнении)
    if db[uid].get("referred_by") and "bonus_given" not in db[uid]:
        ref_id = str(db[uid
