import asyncio
import logging
import json
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, BotCommand

# Настройка логирования для Railway
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# ТОКЕН
TOKEN = "7714657648:AAH1zEV5p2gHHowtYnKHkMnIYX88UirHeGs"

bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_FILE = "balances.json"

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения базы: {e}")
        return {}

def save_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Ошибка записи базы: {e}")

# --- НАСТРОЙКА МЕНЮ ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="topup", description="Пополнить баланс"),
        BotCommand(command="balance", description="Проверить баланс"),
        BotCommand(command="help", description="Инструкция")
    ]
    await bot.set_my_commands(commands)

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🚀 **Бот активирован!**\n"
        "Все функции доступны через меню команд [/].",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 **Инструкция:**\n\n"
        "1️⃣ Найти ID подарков можно тут: @GiftChangesIDs\n"
        "2️⃣ Пополнить баланс бота: `/topup 50`\n"
        "3️⃣ Отправить подарок другу (формат):\n"
        "`ID_пользователя ID_подарка Сообщение`"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    db = load_db()
    user_id = str(message.from_user.id)
    balance = db.get(user_id, 0)
    await message.answer(f"💰 Ваш текущий баланс: **{balance} Stars**", parse_mode="Markdown")

@dp.message(Command("topup"))
async def cmd_topup(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Введите сумму пополнения, например: `/topup 50`", parse_mode="Markdown")
    
    amount = int(parts[1])
    try:
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Пополнение Stars",
            description=f"Покупка {amount} Telegram Stars",
            payload="stars_topup",
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=amount)]
        )
    except Exception as e:
        logger.error(f"Ошибка создания счета: {e}")
        await message.answer("❌ Ошибка при создании счета. Попробуйте позже.")

# --- ПЛАТЕЖИ ---
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: types.Message):
    db = load_db()
    user_id = str(message.from_user.id)
    amount = message.successful_payment.total_amount
    db[user_id] = db.get(user_id, 0) + amount
    save_db(db)
    await message.answer(f"✅ Баланс успешно пополнен на **{amount} Stars**!")

# --- ОТПРАВКА ПОДАРКОВ ---
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_gift_request(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 2 and parts[0].isdigit():
        target_id = int(parts[0])
        gift_id = parts[1]
        text = parts[2] if len(parts) > 2 else ""
        
        try:
            # API метод для отправки подарка
            await bot.send_gift(user_id=target_id, gift_id=gift_id, text=text)
            await message.answer(f"🎁 Подарок `{gift_id}` отправлен пользователю `{target_id}`!")
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {e}\n(Проверьте баланс бота и корректность данных)")
    else:
        await message.answer("ℹ️ Для отправки подарка используйте формат из /help")

# --- ЗАПУСК ---
async def main():
    try:
        await set_commands(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запущен и прослушивает сообщения...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
