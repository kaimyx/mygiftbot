import asyncio
import logging
import json
import os
import math
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, BotCommand

# --- КОНФИГУРАЦИЯ ---
TOKEN = "7714657648:AAH1zEV5p2gHHowtYnKHkMnIYX88UirHeGs"
ADMIN_ID = 123456789  # ОБЯЗАТЕЛЬНО ПОСТАВЬ СВОЙ ID
DB_FILE = "gift_db.json"
PERCENT_FEE = 0.15      
GIFT_PRICE = 50         

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding='utf-8') as f:
        try: return json.load(f)
        except: return {}

def save_db(data):
    with open(DB_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_user(db, user_id):
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"balance": 0, "history": [], "sent_count": 0}
    return db

async def resolve_id(text):
    text = text.strip()
    if text.isdigit(): return int(text)
    if text.startswith("@"):
        try:
            chat = await bot.get_chat(text)
            return chat.id
        except: return None
    return None

# --- МЕНЮ КОМАНД ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="balance", description="Мой баланс 💰"),
        BotCommand(command="profile", description="Личный кабинет 👤"),
        BotCommand(command="history", description="История подарков 📜"),
        BotCommand(command="topup", description="Пополнить баланс ⭐"),
        BotCommand(command="help", description="Инструкция 📖")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db = load_db()
    init_user(db, message.from_user.id)
    save_db(db)
    await message.answer("🚀 Бот активирован!\nВсе функции доступны через меню команд /.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    instruction = (
        "📖 **Инструкция:**\n\n"
        "1️⃣ Найти ID подарков: @GiftExcuseId\n"
        "2️⃣ Пополнить баланс: `/topup 100` (Комиссия: 15%)\n"
        "3️⃣ Отправить подарок (формат):\n"
        "`ID_пользователя ID_подарка Сообщение`"
    )
    await message.answer(instruction, parse_mode="Markdown")

# --- ВКЛАДКА БАЛАНСА ---
@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    user = db.get(uid, {"balance": 0})
    
    if int(uid) == ADMIN_ID:
        text = "💰 **Ваш баланс:**\nИспользуются 50 Stars на аккаунте (Admin Access)."
    else:
        text = f"💰 **Ваш баланс:** {user['balance']} Stars"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    user = db.get(uid, {"balance": 0, "sent_count": 0})
    
    if int(uid) == ADMIN_ID:
        balance_info = "Готов (Admin)"
    else:
        balance_info = f"{user['balance']} Stars"
    
    text = (
        f"👤 **Личный кабинет**\n\n"
        f"🆔 ID: `{uid}`\n"
        f"💰 Баланс: **{balance_info}**\n"
        f"🎁 Отправлено: {user['sent_count']}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    db = load_db()
    history = db.get(str(message.from_user.id), {}).get("history", [])
    if not history: return await message.answer("📜 Твоя история пуста.")
    await message.answer("📜 **Последние подарки:**\n\n" + "\n".join(history[-10:]), parse_mode="Markdown")

@dp.message(Command("topup"))
async def cmd_topup(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return await message.answer("⚠️ Пример: `/topup 100`")
    amount = int(parts[1])
    total = amount + math.ceil(amount * PERCENT_FEE)
    await bot.send_invoice(message.chat.id, title="Пополнение Stars", description=f"Зачисление: {amount} ⭐", payload=f"up_{amount}", currency="XTR", prices=[LabeledPrice(label="Stars", amount=total)])

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    amount = int(message.successful_payment.invoice_payload.split("_")[1])
    db[uid]["balance"] += amount
    save_db(db)
    await message.answer(f"✅ Баланс пополнен на **{amount} Stars**!")

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_gift_sending(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) < 2: return 

    target_input, gift_id = parts[0], parts[1]
    gift_msg = " ".join(parts[2:]) if len(parts) > 2 else ""
    
    db = load_db()
    uid = str(message.from_user.id)
    init_user(db, uid)

    if int(uid) != ADMIN_ID and db[uid]["balance"] < GIFT_PRICE:
        return await message.answer(f"❌ Недостаточно Stars! Баланс: {db[uid]['balance']}")

    target_id = await resolve_id(target_input)
    if not target_id: return await message.answer("❌ Пользователь не найден.")

    try:
        await bot.send_gift(user_id=target_id, gift_id=gift_id, text=gift_msg, is_anonymous=False)
        if int(uid) != ADMIN_ID: db[uid]["balance"] -= GIFT_PRICE
        db[uid]["sent_count"] += 1
        db[uid]["history"].append(f"🎁 {gift_id} -> {target_input}")
        save_db(db)
        await message.answer(f"✅ Подарок успешно отправлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка API: {e}")

async def main():
    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
