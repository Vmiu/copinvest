from datetime import timedelta

SESSION_TIMEOUT = timedelta(minutes=30)


async def get_or_create_session(db, user_id: str) -> str:
    raise NotImplementedError
