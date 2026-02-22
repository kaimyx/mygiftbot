import asyncio
import logging
import json
import os
import sys
import math
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, BotCommand

# Логирование
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = "7714657648:AAH1zEV5p2gHHowtYnKHkMnIYX88UirHeGs"
bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_FILE = "balances.json"

# НАСТРОЙКИ
PERCENT_FEE = 0.15  # Комиссия 15%
GIFT_COST = 50      # СТОИМОСТЬ ОТПРАВКИ ОДНОГО ПОДАРКА (измени под свою цену)

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
        return {}
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {}

def save_db(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
    except: pass

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить"),
        BotCommand(command="topup", description="Пополнить"),
        BotCommand(command="balance", description="Баланс"),
        BotCommand(command="help", description="Инструкция")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 **GiftExcuse активирован!**\nДари архивные подарки, которых нет в магазине.\nВсе функции доступны в меню [/].", parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 **Инструкция:**\n\n"
        "1️⃣ Найти ID подарков: @GiftChangesIDs\n"
        "2️⃣ Пополнить баланс: `/topup 100` (Комиссия: 15%)\n"
        "3️⃣ Отправить подарок (формат):\n"
        "`ID_пользователя ID_подарка Сообщение`"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    db = load_db()
    balance = db.get(str(message.from_user.id), 0)
    await message.answer(f"💰 Ваш баланс: **{balance} Stars**\nСтоимость отправки подарка: **{GIFT_COST} Stars**", parse_mode="Markdown")

@dp.message(Command("topup"))
async def cmd_topup(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Пример: `/topup 100`", parse_mode="Markdown")
    
    user_amount = int(parts[1])
    fee_amount = math.ceil(user_amount * PERCENT_FEE)
    total_to_pay = user_amount + fee_amount
    
    try:
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Пополнение Stars",
            description=f"Зачисление: {user_amount} ⭐\nКомиссия: {fee_amount} ⭐",
            payload=f"topup_{user_amount}",
            currency="XTR",
            prices=[LabeledPrice(label=f"Stars + Комиссия", amount=total_to_pay)]
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка платежной системы.")

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: types.Message):
    db = load_db()
    user_id = str(message.from_user.id)
    payload = message.successful_payment.invoice_payload
    amount_to_add = int(payload.split('_')[1])
    
    db[user_id] = db.get(user_id, 0) + amount_to_add
    save_db(db)
    await message.answer(f"✅ Оплата прошла! На баланс зачислено **{amount_to_add} Stars**.")

# --- ЛОГИКА ОТПРАВКИ И СПИСАНИЯ ---
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_gift(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 2 and parts[0].isdigit():
        user_id = str(message.from_user.id)
        db = load_db()
        current_balance = db.get(user_id, 0)

        # 1. Проверка баланса
        if current_balance < GIFT_COST:
            return await message.answer(f"❌ Недостаточно Stars! Стоимость отправки: {GIFT_COST}, ваш баланс: {current_balance}.")

        target_user = int(parts[0])
        gift_id = parts[1]
        gift_text = parts[2] if len(parts) > 2 else ""

        try:
            # 2. Попытка отправки через API
            await bot.send_gift(user_id=target_user, gift_id=gift_id, text=gift_text)
            
            # 3. СПИСАНИЕ СРЕДСТВ ПРИ УСПЕХЕ
            db[user_id] = current_balance - GIFT_COST
            save_db(db)
            
            await message.answer(f"🎁 Подарок отправлен! Списано **{GIFT_COST} Stars**. \nОстаток: **{db[user_id]} Stars**.")
        except Exception as e:
            await message.answer(f"❌ Ошибка при отправке подарка: {e}")
    else:
        await message.answer("ℹ️ Используй формат: `ID_друга ID_подарка Текст` (см. /help)")

async def main():
    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
