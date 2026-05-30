"""
🐕 Random Dog Bot — Telegram bot that sends random dog images.

Deploy on Railway. Set BOT_TOKEN env var in Railway dashboard.
"""

import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DOG_API = "https://dog.ceo/api/breeds/image/random"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message."""
    await update.message.reply_text(
        "🐕 Привет! Я Random Dog Bot!\n\n"
        "Команды:\n"
        "/dog — получить случайное фото собаки"
    )


async def dog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch a random dog image and send it."""
    msg = await update.message.reply_text("🔍 Ищу собачку...")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(DOG_API)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "success" or not data.get("message"):
            await msg.edit_text("😢 Не нашёл собачку. Попробуй ещё раз!")
            return

        image_url = data["message"]
        await msg.delete()
        await update.message.reply_photo(photo=image_url, caption="🐶 Лови собачку!")

    except Exception as e:
        logger.error(f"Dog API error: {e}")
        await msg.edit_text("😢 Ошибка при поиске собачки. Попробуй позже.")


def main() -> None:
    """Start the bot."""
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable is not set!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dog", dog))

    logger.info("🐕 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
