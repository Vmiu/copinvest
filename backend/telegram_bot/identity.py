import json

import structlog

from backend.core.config import get_settings
from backend.models.enums import UserRole

logger = structlog.get_logger()


def get_user_from_telegram_id(telegram_user_id: int) -> dict | None:
    """Return {"user_id": str, "role": str} for a registered Telegram user, or None."""
    settings = get_settings()
    try:
        user_map = json.loads(settings.telegram_user_map)
    except json.JSONDecodeError:
        logger.error("telegram_user_map_invalid_json")
        return None
    entry = user_map.get(str(telegram_user_id))
    if entry is None:
        return None
    role = entry.get("role", "")
    if role not in {r.value for r in UserRole}:
        logger.warning("telegram_user_invalid_role", role=role)
        return None
    return entry
