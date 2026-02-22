import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# Включаем логирование на максимум, чтобы увидеть ошибку в Railway
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = "7714657648:AAH1zEV5p2gHHowtYnKHkMnIYX88UirHeGs"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🚀 Бот в сети! Railway работает!")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer("📖 Инструкция:\nОтправь: `ID Подарок Текст`")

@dp.message()
async def send_gift_handler(message: types.Message):
    if not message.text or message.text.startswith('/'): return
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 2 and parts[0].isdigit():
        try:
            # Метод API для подарков
            await bot.send_gift(user_id=int(parts[0]), gift_id=parts[1], text=parts[2] if len(parts)>2 else "")
            await message.answer("✅ Подарок отправлен!")
        except Exception as e:
            await message.answer(f"❌ Ошибка API: {e}")

async def main():
    logger.info("Пытаюсь запустить polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Бот упал с ошибкой: {e}")

if __name__ == "__main__":
    asyncio.run(main())
