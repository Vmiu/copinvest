from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from backend.core.config import get_settings
from backend.telegram_bot.handlers import (
    AWAITING_EDIT,
    handle_action,
    handle_brief,
    handle_edit_reply,
    handle_followup,
    handle_product,
    handle_unknown_text,
)


def main() -> None:
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set — bot cannot start")

    chunking_client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )
    generation_client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )
    qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data.update({
        "chunking_client": chunking_client,
        "generation_client": generation_client,
        "qdrant_client": qdrant_client,
    })

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("brief", handle_brief),
            CommandHandler("product", handle_product),
            CommandHandler("followup", handle_followup),
            CallbackQueryHandler(handle_action),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown_text),
        ],
        states={
            AWAITING_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_reply),
                CallbackQueryHandler(handle_action),
            ]
        },
        fallbacks=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown_text),
        ],
        per_user=True,
        per_chat=True,
        per_message=False,
        conversation_timeout=300,
    )
    app.add_handler(conv)

    app.run_polling()
