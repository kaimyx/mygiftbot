import asyncio
import logging
import json
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, BotCommand

# Настройка логирования для Railway (чтобы видеть ошибки в логах)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# ТОКЕН
TOKEN = "7714657648:AAH1zEV5p2gHHowtYnKHkMnIYX88UirHeGs"

bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_FILE = "user_balances.json"

# --- БЕЗОПАСНАЯ РАБОТА С БАЗОЙ ---
def load_data():
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

def save_data(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Ошибка записи базы: {e}")

# --- КОМАНДЫ ---
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="topup", description="Пополнить Stars"),
        BotCommand(command="balance", description="Мой баланс"),
        BotCommand(command="help", description="Инструкция")
    ]
    await bot.set_my_commands(main_menu_commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("✅ **Бот успешно запущен на Railway!**\nИспользуй /help для инструкции.", parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    balance = data.get(user_id, 0)
    await message.answer(f"💰 Ваш баланс: **{balance} Stars**", parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "🎁 **Как отправить подарок через API:**\n\n"
        "Отправь сообщение форматом:\n"
        "`ID_пользователя ID_подарка Текст` (без косой черты)\n\n"
        "**Пример:** `1234567 220 С днюхой!`\n\n"
        "Пополнить баланс: `/topup 100`"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("topup"))
async def cmd_topup(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            return await message.answer("⚠️ Укажите сумму, например: `/topup 50`", parse_mode="Markdown")
        
        amount = int(parts[1])
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Пополнение баланса",
            description=f"Покупка {amount} Telegram Stars",
            payload=f"user_{message.from_user.id}",
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=amount)]
        )
    except ValueError:
        await message.answer("❌ Сумма должна быть числом!")
    except Exception as e:
        logger.error(f"Ошибка инвойса: {e}")

# --- ПЛАТЕЖИ ---
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: types.Message):
    user_id = str(message.from_user.id)
    amount = message.successful_payment.total_amount
    data = load_data()
    data[user_id] = data.get(user_id, 0) + amount
    save_data(data)
    await message.answer(f"⭐ Баланс пополнен на **{amount}**!")

# --- ОТПРАВКА ПОДАРКОВ (API) ---
@dp.message()
async def handle_gift(message: types.Message):
    if not message.text or message.text.startswith('/'):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) >= 2 and parts[0].isdigit():
        target_id = int(parts[0])
        gift_id = parts[1]
        comment = parts[2] if len(parts) > 2 else ""
