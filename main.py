import asyncio
import logging
import json
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, BotCommand

# ТОКЕН (Твой рабочий токен)
TOKEN = "7714657648:AAH1zEV5p2gHHowtYnKHkMnIYX88UirHeGs"

# Настройка логирования, чтобы видеть ошибки в Railway
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_FILE = "user_balances.json"

# --- РАБОТА С БАЗОЙ ДАННЫХ (БАЛАНС) ---
def get_balances():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def add_balance(user_id, amount):
    data = get_balances()
    data[str(user_id)] = data.get(str(user_id), 0) + amount
    with open(DB_FILE, "w") as f: json.dump(data, f)

# --- НАСТРОЙКА МЕНЮ КОМАНД ---
async def setup_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="topup", description="Пополнить Stars"),
        BotCommand(command="balance", description="Мои пополнения"),
        BotCommand(command="help", description="Инструкция и ID")
    ]
    await bot.set_my_commands(commands)

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 **Бот GiftExcuse запущен!**\n\nИспользуйте меню или команды:\n/topup — пополнить баланс\n/balance — проверить вклад\n/help — как отправить подарок", parse_mode="Markdown")

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    balances = get_balances()
    user_sum = balances.get(str(message.from_user.id), 0)
    await message.answer(f"💰 **Ваш текущий баланс:** {user_sum} Stars", parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 **Как отправить подарок через API:**\n\n"
        "Отправьте боту сообщение в формате:\n"
        "`ID_пользователя ID_подарка Текст` (без команд)\n\n"
        "**Пример:** `1234567 220 Спасибо!`\n\n"
        "1️⃣ Найти ID подарков: @GiftChangesIDs\n"
        "2️⃣ Пополнение баланса: `/topup 50
