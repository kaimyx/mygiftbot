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
ADMIN_ID = 123456789  # ЗАМЕНИ НА СВОЙ ID
DB_FILE = "gift_db.json"
PERCENT_FEE = 0.15      
GIFT_PRICE = 50  # Стоимость отправки одного подарка через бота (если нужно)

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

# --- МЕНЮ КОМАНД ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="balance", description="Мой баланс 💰"),
        BotCommand(command="profile", description="Личный кабинет 👤"),
        BotCommand(command="history", description="История 📜"),
        BotCommand(command="topup", description="Пополнить ⭐️"),
        BotCommand(command="help", description="Инструкция 📖")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db = load_db()
    init_user(db, message.from_user.id)
    save_db(db)
    await message.answer("🚀 **Бот готов к отправке подарков!**\n\nИспользуйте меню или команду /help для ознакомления с форматом.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    instruction = (
        "📖 **Инструкция по отправке подарка:**\n\n"
        "Отправьте сообщение в формате:\n"
        "`ID_пользователя ID_подарка Сообщение` (сообщение не обязательно)\n\n"
        "**Пример:**\n"
        "`12345678 999 С днем рождения!`\n\n"
        "📌 *Где взять ID подарка?* Обычно в специальных каналах или через @GiftExcuseId.\n"
        "📌 *Стоимость отправки:* 50 Stars (с баланса бота)."
    )
    await message.answer(instruction, parse_mode="Markdown")

# --- ПРОФИЛЬ И БАЛАНС ---
@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    db = load_db()
    user = init_user(db, message.from_user.id)[str(message.from_user.id)]
    
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"💰 **Баланс:** Безлимит (Admin)\nДоступно Stars на аккаунте бота.")
    else:
        await message.answer(f"💰 **Ваш баланс:** {user['balance']} Stars")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    user = init_user(db, uid)[uid]
    
    text = (
        f"👤 **Личный кабинет**\n\n"
        f"🆔 Ваш ID: `{uid}`\n"
        f"💰 Баланс: **{user['balance'] if int(uid) != ADMIN_ID else '∞'}**\n"
        f"🎁 Отправлено подарков: {user['sent_count']}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    db = load_db()
    user = init_user(db, message.from_user.id)[str(message.from_user.id)]
    if not user["history"]: 
        return await message.answer("📜 Ваша история подарков пока пуста.")
    
    history_text = "\n".join(user["history"][-10:])
    await message.answer(f"📜 **Последние 10 отправлений:**\n\n{history_text}", parse_mode="Markdown")

# --- ПОПОЛНЕНИЕ ---
@dp.message(Command("topup"))
async def cmd_topup(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): 
        return await message.answer("⚠️ Формат: `/topup 100` (где 100 — сумма зачисления)")
    
    amount = int(parts[1])
    total_to_pay = amount + math.ceil(amount * PERCENT_FEE)
    
    await bot.send_invoice(
        message.chat.id,
        title="Пополнение баланса",
        description=f"Зачисление {amount} Stars на внутренний баланс.",
        payload=f"topup_{amount}",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=total_to_pay)]
    )

@dp.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def on_success_pay(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    init_user(db, uid)
    
    amount = int(message.successful_payment.invoice_payload.split("_")[1])
    db[uid]["balance"] += amount
    save_db(db)
    
    await message.answer(f"✅ Успешно! Вам зачислено **{amount} Stars**.")

# --- ЛОГИКА ОТПРАВКИ ПОДАРКА ---
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_gift_transfer(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        return # Игнорируем простые сообщения

    target_id_raw = parts[0]
    gift_id = parts[1]
    text_note = parts[2] if len(parts) > 2 else ""

    # Проверка ID получателя
    if not target_id_raw.isdigit():
        return await message.answer("❌ ID пользователя должен состоять из цифр.")
    
    target_id = int(target_id_raw)
    db = load_db()
    uid = str(message.from_user.id)
    init_user(db, uid)

    # Проверка баланса (админу бесплатно)
    if int(uid) != ADMIN_ID and db[uid]["balance"] < GIFT_PRICE:
        return await message.answer(f"❌ Недостаточно средств. Нужно: {GIFT_PRICE} Stars.\nВаш баланс: {db[uid]['balance']}")

    try:
        # Основной метод Telegram API для отправки подарка
        await bot.send_gift(
            user_id=target_id,
            gift_id=gift_id,
            text=text_note
        )

        # Списание и логгирование
        if int(uid) != ADMIN_ID:
            db[uid]["balance"] -= GIFT_PRICE
        
        db[uid]["sent_count"] += 1
        db[uid]["history"].append(f"🎁 Подарок `{gift_id}` для ID `{target_id}`")
        save_db(db)

        await message.answer(f"✅ Подарок успешно отправлен пользователю `{target_id}`!")

    except Exception as e:
        logging.error(f"Gift Error: {e}")
        await message.answer(f"❌ Ошибка при отправке: {str(e)}\n\n*Убедитесь, что ID подарка верный и бот имеет Stars на счету.*")

# --- ЗАПУСК ---
async def main():
    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
