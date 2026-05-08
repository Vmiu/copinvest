import json

from backend.core.config import get_settings


def get_user_from_telegram_id(telegram_user_id: int) -> dict | None:
    """Return {"user_id": str, "role": str} for a registered Telegram user, or None."""
    settings = get_settings()
    user_map = json.loads(settings.telegram_user_map)
    return user_map.get(str(telegram_user_id))
