import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from backend.core.database import async_session
from backend.repositories import audit_repo
from backend.services.query_service import process_query
from backend.telegram_bot.identity import get_user_from_telegram_id

logger = structlog.get_logger()

AWAITING_EDIT = 1

_HELP_TEXT = (
    "Please use one of these commands:\n\n"
    "/brief <topic or client> — prepare a meeting brief\n"
    "/product <product name> — summarize product information\n"
    "/followup <context> — draft a compliant follow-up note"
)


def _get_verified_user(update: Update):
    """Return internal user dict or None if unregistered."""
    if update.effective_user is None:
        return None
    return get_user_from_telegram_id(update.effective_user.id)


async def _run_query(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, intent: str) -> int:
    """Shared pipeline: embed → retrieve → generate → send draft with keyboard."""
    user = _get_verified_user(update)
    if user is None:
        await update.message.reply_text(
            "Your Telegram account is not registered. Contact your administrator."
        )
        return ConversationHandler.END

    if not query.strip():
        await update.message.reply_text(_HELP_TEXT)
        return ConversationHandler.END

    await update.message.chat.send_action("typing")

    session_id = context.user_data.get("session_id")
    chunking_client = context.bot_data["chunking_client"]
    generation_client = context.bot_data["generation_client"]
    qdrant_client = context.bot_data["qdrant_client"]

    try:
        async with async_session() as db:
            result = await process_query(
                db=db,
                query=query,
                session_id=session_id,
                user_id=user["user_id"],
                user_role=user["role"],
                chunking_client=chunking_client,
                generation_client=generation_client,
                qdrant_client=qdrant_client,
                channel=f"telegram/{intent}",
                intent=intent,
            )
            await db.commit()
    except Exception as exc:
        logger.error("telegram_query_error", error=str(exc), intent=intent)
        await update.message.reply_text("Something went wrong — please try again.")
        return ConversationHandler.END

    context.user_data["trace_id"] = result["trace_id"]
    context.user_data["session_id"] = result.get("session_id", session_id)

    answer = result["answer"]
    sources = result.get("sources", [])
    if sources:
        source_lines = "\n".join(f"• {s['doc_name']}" + (f" — {s['section_title']}" if s.get("section_title") else "") for s in sources)
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


async def handle_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /brief <topic> — generate a meeting brief."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /brief <client name or topic>")
        return ConversationHandler.END
    return await _run_query(update, context, query, intent="brief")


async def handle_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /product <name> — summarize product information."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /product <product name>")
        return ConversationHandler.END
    return await _run_query(update, context, query, intent="product")


async def handle_followup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /followup <context> — draft a compliant follow-up note."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /followup <meeting context or client name>")
        return ConversationHandler.END
    return await _run_query(update, context, query, intent="followup")


async def handle_unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reject plain text — guide user to the three commands."""
    await update.message.reply_text(_HELP_TEXT)
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
