import structlog
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from backend.core.database import async_session
from backend.services.query_service import process_query
from backend.telegram_bot.identity import get_user_from_telegram_id

logger = structlog.get_logger()


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages: run RAG pipeline, send sourced answer."""
    if update.effective_user is None:
        return

    user = get_user_from_telegram_id(update.effective_user.id)
    if user is None:
        await update.message.reply_text(
            "Your Telegram account is not registered. Contact your administrator."
        )
        return

    await update.message.chat.send_action("typing")

    session_id = context.user_data.get("session_id")
    chunking_client = context.bot_data["chunking_client"]
    generation_client = context.bot_data["generation_client"]
    qdrant_client = context.bot_data["qdrant_client"]

    try:
        async with async_session() as db:
            result = await process_query(
                db=db,
                query=update.message.text,
                session_id=session_id,
                user_id=user["user_id"],
                user_role=user["role"],
                chunking_client=chunking_client,
                generation_client=generation_client,
                qdrant_client=qdrant_client,
                channel="telegram",
            )
            await db.commit()
    except Exception as exc:
        logger.error("telegram_query_error", error=str(exc))
        await update.message.reply_text("Something went wrong — please try again.")
        return

    context.user_data["session_id"] = result.get("session_id", session_id)

    answer = result["answer"]
    sources = result.get("sources", [])
    if sources:
        source_lines = "\n".join(
            f"• {s['doc_name']}" + (f" — {s['section_title']}" if s.get("section_title") else "")
            for s in sources
        )
        reply = f"{answer}\n\nSources:\n{source_lines}"
    else:
        reply = answer

    await update.message.reply_text(reply)
