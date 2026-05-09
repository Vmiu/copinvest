from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from telegram.ext import (
    Application,
    ConversationHandler,
    MessageHandler,
    filters,
)

from backend.core.config import get_settings
from backend.telegram_bot.handlers import handle_query


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

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))

    app.run_polling()
