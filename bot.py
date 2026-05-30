"""
🐕🐱 Animal Bot — Telegram bot with random dog & cat photos + inline buttons.

Deploy on Railway. Set BOT_TOKEN env var in Railway dashboard.
"""

import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DOG_API = "https://dog.ceo/api/breeds/image/random"
CAT_API = "https://api.thecatapi.com/v1/images/search"
IMAGINE_BASE = "https://image.pollinations.ai/prompt"

# Allowed image generation models (Pollinations.ai)
IMAGINE_MODELS = {
    "flux": "FLUX (best quality)",
    "turbo": "Turbo (fast)",
    "flux-realism": "FLUX Realism (photorealistic)",
    "any-dark": "Dark fantasy",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with inline buttons."""
    keyboard = [
        [
            InlineKeyboardButton("🐕 Собаку", callback_data="dog"),
            InlineKeyboardButton("🐱 Кота", callback_data="cat"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🐾 Привет! Я Animal Bot!\n\n"
        "Выбери, кого хочешь увидеть:\n\n"
        "🎨 Ещё могу нарисовать что угодно —\n"
        "напиши /imagine твой запрос",
        reply_markup=reply_markup,
    )


async def dog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch a random dog image and send it with buttons."""
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
        await _send_with_buttons(update, image_url, "🐶 Лови собачку!")

    except Exception as e:
        logger.error(f"Dog API error: {e}")
        await msg.edit_text("😢 Ошибка при поиске собачки. Попробуй позже.")


async def cat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch a random cat image and send it with buttons."""
    msg = await update.message.reply_text("🔍 Ищу котика...")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CAT_API)
            resp.raise_for_status()
            data = resp.json()

        if not data or not data[0].get("url"):
            await msg.edit_text("😢 Не нашёл котика. Попробуй ещё раз!")
            return

        image_url = data[0]["url"]
        await msg.delete()
        await _send_with_buttons(update, image_url, "🐱 Лови котика!")

    except Exception as e:
        logger.error(f"Cat API error: {e}")
        await msg.edit_text("😢 Ошибка при поиске котика. Попробуй позже.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()

    if query.data == "dog":
        msg = await query.edit_message_text("🔍 Ищу собачку...")
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
            await query.message.reply_photo(
                photo=image_url,
                caption="🐶 Лови собачку!",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🐕 Ещё собаку", callback_data="dog"),
                        InlineKeyboardButton("🐱 Кота", callback_data="cat"),
                    ],
                ]),
            )
        except Exception as e:
            logger.error(f"Dog API error: {e}")
            await msg.edit_text("😢 Ошибка. Попробуй позже.")

    elif query.data == "cat":
        msg = await query.edit_message_text("🔍 Ищу котика...")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(CAT_API)
                resp.raise_for_status()
                data = resp.json()

            if not data or not data[0].get("url"):
                await msg.edit_text("😢 Не нашёл котика. Попробуй ещё раз!")
                return

            image_url = data[0]["url"]
            await msg.delete()
            await query.message.reply_photo(
                photo=image_url,
                caption="🐱 Лови котика!",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🐕 Собаку", callback_data="dog"),
                        InlineKeyboardButton("🐱 Ещё кота", callback_data="cat"),
                    ],
                ]),
            )
        except Exception as e:
            logger.error(f"Cat API error: {e}")
            await msg.edit_text("😢 Ошибка. Попробуй позже.")


async def imagine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate an image from text prompt via Pollinations.ai."""
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text(
            "🎨 Напиши запрос после команды.\n\n"
            "Пример: /imagine рыцарь на драконе\n\n"
            "Можно указать модель в конце: /imagine кот в скафандре flux\n"
            "Доступные модели: " + ", ".join(IMAGINE_MODELS.keys())
        )
        return

    msg = await update.message.reply_text("🎨 Генерирую изображение...")

    # Check if last word is a known model
    words = prompt.rsplit(None, 1)
    model = "flux"
    text = prompt
    if len(words) == 2 and words[1].lower() in IMAGINE_MODELS:
        model = words[1].lower()
        text = words[0]

    try:
        import urllib.parse
        encoded = urllib.parse.quote(text)
        image_url = f"{IMAGINE_BASE}/{encoded}?width=1024&height=1024&model={model}&nologo=true"

        await msg.delete()
        await update.message.reply_photo(
            photo=image_url,
            caption=f"🎨 {text}\n🤖 Модель: {IMAGINE_MODELS.get(model, model)}",
        )
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        await msg.edit_text("😢 Ошибка при генерации. Попробуй другой запрос.")


async def _send_with_buttons(update: Update, photo_url: str, caption: str) -> None:
    """Helper: send a photo with inline buttons below."""
    keyboard = [
        [
            InlineKeyboardButton("🐕 Собаку", callback_data="dog"),
            InlineKeyboardButton("🐱 Кота", callback_data="cat"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_photo(photo=photo_url, caption=caption, reply_markup=reply_markup)


def main() -> None:
    """Start the bot."""
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable is not set!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dog", dog))
    app.add_handler(CommandHandler("cat", cat))
    app.add_handler(CommandHandler("imagine", imagine))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🐾 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
