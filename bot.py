"""
🤖 Personal Assistant Bot — forwards messages from users to the owner.

Deploy on Railway. Set BOT_TOKEN env var.
"""

import os
import json
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Owner's Telegram ID (hardcoded for security — only Игорь gets these)
OWNER_ID = 6023070081
MAPPING_FILE = Path("user_mapping.json")


def load_mapping() -> dict:
    """Load user mapping (forwarded_msg_id -> user chat_id)."""
    if MAPPING_FILE.exists():
        return json.loads(MAPPING_FILE.read_text())
    return {}


def save_mapping(mapping: dict) -> None:
    """Save user mapping to disk."""
    MAPPING_FILE.write_text(json.dumps(mapping, indent=2))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route messages: users → owner, owner replies → user."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    if chat_id == OWNER_ID:
        # ── Owner is sending a message ──────────────────────────
        reply = update.message.reply_to_message
        if reply and reply.message_id:
            mapping = load_mapping()
            target_user_id = mapping.get(str(reply.message_id))
            if target_user_id:
                # Forward owner's reply to the original user
                text = update.message.text or update.message.caption or ""
                if text:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=f"📩 Ответ от Игоря:\n\n{text}",
                    )
                elif update.message.photo:
                    await context.bot.send_photo(
                        chat_id=target_user_id,
                        photo=update.message.photo[-1].file_id,
                        caption=f"📩 Ответ от Игоря: {update.message.caption or ''}",
                    )
                else:
                    await update.message.reply_text("❌ Такой тип сообщения пока не поддерживается для ответа.")
                    return

                await update.message.reply_text("✅ Ответ отправлен пользователю!")
                return

        await update.message.reply_text(
            "👋 Привет, Игорь!\n\n"
            "Все сообщения от пользователей пересылаются сюда.\n"
            "Чтобы ответить — просто ответь на пересланное сообщение."
        )

    else:
        # ── A user is sending a message ─────────────────────────
        user_info = f"@{user.username}" if user.username else user.full_name
        display_name = f"{user.full_name} (@{user.username})" if user.username else user.full_name

        # Forward message to owner
        text = update.message.text or update.message.caption or ""
        forwarded = None

        if text:
            forwarded = await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"📨 От: {display_name} [ID: {chat_id}]\n\n{text}",
            )
        elif update.message.photo:
            caption = update.message.caption or ""
            forwarded = await context.bot.send_photo(
                chat_id=OWNER_ID,
                photo=update.message.photo[-1].file_id,
                caption=f"📨 Фото от: {display_name} [ID: {chat_id}]\n{caption}",
            )
        elif update.message.voice:
            forwarded = await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"📨 Голосовое от: {display_name} [ID: {chat_id}]",
            )
        else:
            await update.message.reply_text(
                "🤖 Этот бот — личный ассистент Игоря. "
                "Ваше сообщение не поддерживается, попробуйте текст или фото."
            )
            return

        # Store mapping so owner can reply
        if forwarded:
            mapping = load_mapping()
            mapping[str(forwarded.message_id)] = chat_id
            save_mapping(mapping)

        await update.message.reply_text(
            f"✅ Сообщение отправлено Игорю! Он ответит вам в ближайшее время."
        )
        logger.info(f"Message from {chat_id} ({display_name}) → forwarded to owner")


def main() -> None:
    """Start the bot."""
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN is not set!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logger.info("🤖 Assistant bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
