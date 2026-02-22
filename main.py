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
ADMIN_ID = 123456789 
DB_FILE = "gift_db.json"
PERCENT_FEE = 0.15

SHOP_ITEMS = {
    "220": ["Rare Blue Star", 50],
    "350": ["Vintage Heart", 75],
    "500": ["Golden Rocket", 150]
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding='utf-8') as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def init_user(db, user_id):
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"balance": 0, "history": [], "sent_count": 0}
    return db

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def resolve_id(text):
    if text.isdigit(): return int(text)
    try:
        chat = await bot.get_chat(text if text.startswith("@") else f"@{text}")
        return chat.id
    except: return None

# --- КОМАНДЫ ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="profile", description="Личный кабинет 👤"),
        BotCommand(command="shop", description="Магазин подарков 🎁"),
        BotCommand(command="history", description="История заказов 📜"),
        BotCommand(command="topup", description="Пополнить баланс ⭐")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db = load_db()
    init_user(db, message.from_user.id)
    save_db(db)
    await message.answer("🎁 **Добро пожаловать в GiftExcuse!**\n\nИспользуй /shop для выбора подарка.\nТвой личный кабинет: /profile")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    db = load_db()
    uid = str(message.from_user.id)
    user = db.get(uid, {"balance": 0, "sent_count": 0})
    
    text = (
        f"👤 **Личный кабинет**\n\n"
        f"🆔 Твой ID: `{uid}`\n"
        f"💰 Баланс: {user['balance']} ⭐\n"
        f"📦 Отправлено подарков: {user['sent_count']}\n\n"
        f"Чтобы пополнить: `/topup сумма`"
    )
    
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="📜 История", callback_data="show_history"))
    kb.add(InlineKeyboardButton(text="➕ Пополнить", callback_data="go_topup"))
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(Command("history"))
@dp.callback_query(F.data == "show_history")
async def show_history(event):
    # Работает и как команда, и как кнопка
    user_id = event.from_user.id
    db = load_db()
    history = db.get(str(user_id), {}).get("history", [])
    
    if not history:
        msg = "📜 Твоя история пока пуста."
    else:
        msg = "📜 **Последние 10 операций:**\n\n" + "\n".join(history[-10:])
    
    if isinstance(event, types.Message):
        await event.answer(msg, parse_mode="Markdown")
    else:
        await event.message.edit_text(msg, parse_mode="Markdown")

# --- ЛОГИКА ОТПРАВКИ (С АНОНИМНОСТЬЮ) ---
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_gift_logic(message: types.Message):
    # Формат: [анонимно] @username ID Сообщение
    text = message.text.lower()
    is_anon = False
    
    if text.startswith("анонимно"):
        is_anon = True
        parts = message.text.split(maxsplit=3)[1:] # Убираем слово "анонимно"
    else:
        parts = message.text.split(maxsplit=2)

    if len(parts) < 2:
        return await message.answer("ℹ️ Формат: `[анонимно] @username ID_подарка Текст`")

    target_user, gift_id = parts[0], parts[1]
    gift_msg = parts[2] if len(parts) > 2 else ""
    
    db = load_db()
    uid = str(message.from_user.id)
    cost = SHOP_ITEMS.get(gift_id, ["", 50])[1]

    if db.get(uid, {}).get("balance", 0) < cost:
        return await message.answer(f"❌ Недостаточно Stars! Твой баланс: {db[uid]['balance']}")

    target_id = await resolve_id(target_user)
    if not target_id:
        return await message.answer("❌ Не удалось найти пользователя.")

    try:
        # ПАРАМЕТР is_anonymous — КЛЮЧЕВАЯ ФУНКЦИЯ
        await bot.send_gift(
            user_id=target_id, 
            gift_id=gift_id, 
            text=gift_msg, 
            is_anonymous=is_anon 
        )
        
        db[uid]["balance"] -= cost
        db[uid]["sent_count"] += 1
        status = "🕵️ Анонимно" if is_anon else "🎁 Публично"
        db[uid]["history"].append(f"{status}: ID {gift_id} -> {target_user}")
        save_db(db)
        
        await message.answer(f"✅ Успешно! {'Анонимно ' if is_anon else ''}отправлено {target_user}. Баланс: {db[uid]['balance']}")
    except Exception as e:
        await message.answer(f"❌ Ошибка API: {e}")

# ... (Код для оплаты Stars остается прежним) ...

async def main():
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
