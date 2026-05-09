import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from backend.core.database import async_session
from backend.repositories import audit_repo
from backend.services.query_service import process_query
from backend.telegram_bot.identity import get_user_from_telegram_id

logger = structlog.get_logger()

AWAITING_EDIT = 1


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming text messages: run RAG pipeline, send draft with inline keyboard."""
    if update.effective_user is None:
        return ConversationHandler.END
    telegram_user_id = update.effective_user.id

    user = get_user_from_telegram_id(telegram_user_id)
    if user is None:
        await update.message.reply_text(
            "Your Telegram account is not registered. Contact your administrator."
        )
        return ConversationHandler.END

    await update.message.chat.send_action("typing")

    query_text = update.message.text
    session_id = context.user_data.get("session_id")

    chunking_client = context.bot_data["chunking_client"]
    generation_client = context.bot_data["generation_client"]
    qdrant_client = context.bot_data["qdrant_client"]

    try:
        async with async_session() as db:
            result = await process_query(
                db=db,
                query=query_text,
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
        return ConversationHandler.END

    context.user_data["trace_id"] = result["trace_id"]
    context.user_data["session_id"] = result.get("session_id", session_id)

    answer = result["answer"]
    sources = result.get("sources", [])
    if sources:
        source_lines = "\n".join(
            f"• {s['doc_name']}" + (f" — {s['section_title']}" if s.get("section_title") else "")
            for s in sources
        )
        draft_text = f"{answer}\n\nSources:\n{source_lines}"
    else:
        draft_text = answer

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Approve", callback_data="approve"),
        InlineKeyboardButton("✏ Edit", callback_data="edit"),
        InlineKeyboardButton("✗ Discard", callback_data="discard"),
    ]])
    await update.message.reply_text(draft_text, reply_markup=keyboard)
    return ConversationHandler.END


async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Approve / Edit / Discard inline keyboard callbacks."""
    callback = update.callback_query
    await callback.answer()

    action = callback.data  # "approve" | "edit" | "discard"
    trace_id = context.user_data.get("trace_id")

    await callback.edit_message_reply_markup(reply_markup=None)

    if action == "edit":
        await callback.message.reply_text("Send your revised version:")
        return AWAITING_EDIT

    if action == "approve":
        audit_action = "approved"
        confirm_text = "Response approved and recorded."
        if trace_id:
            async with async_session() as db:
                audit_row = await audit_repo.get_audit_by_id(db, trace_id)
                final_response = audit_row.llm_response if audit_row else None
                await audit_repo.update_adviser_action(db, trace_id, audit_action, final_response)
                await db.commit()
    else:  # discard
        audit_action = "discarded"
        confirm_text = "Response discarded."
        if trace_id:
            async with async_session() as db:
                await audit_repo.update_adviser_action(db, trace_id, audit_action, None)
                await db.commit()

    await callback.message.reply_text(confirm_text)
    return ConversationHandler.END


async def handle_edit_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the adviser's replacement text after selecting Edit."""
    replacement = update.message.text
    trace_id = context.user_data.get("trace_id")

    if trace_id:
        async with async_session() as db:
            await audit_repo.update_adviser_action(db, trace_id, "edited", replacement)
            await db.commit()

    await update.message.reply_text("Revised response recorded.")
    return ConversationHandler.END
