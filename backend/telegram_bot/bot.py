from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from backend.core.config import get_settings
from backend.telegram_bot.handlers import AWAITING_EDIT, handle_action, handle_edit_reply, handle_query


async def main() -> None:
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

    bot_context = {
        "chunking_client": chunking_client,
        "generation_client": generation_client,
        "qdrant_client": qdrant_client,
    }

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data.update(bot_context)

    # Standalone handler for approve/discard callbacks (fires regardless of conversation state)
    app.add_handler(CallbackQueryHandler(handle_action))

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query)],
        states={AWAITING_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_reply)]},
        fallbacks=[],
        per_user=True,
        per_chat=True,
        conversation_timeout=300,  # 5 minutes
    )
    app.add_handler(conv)

    await app.run_polling()
