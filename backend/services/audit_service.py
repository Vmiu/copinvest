async def create_audit_record(db, user_id: str, query_text: str,
                              session_id: str, channel: str):
    raise NotImplementedError


async def update_retrieval(db, audit, chunks_json: str, max_tier: int,
                           prompt: str) -> None:
    raise NotImplementedError


async def update_generation(db, audit, llm_response: str, model_used: str,
                            prompt_tokens: int, completion_tokens: int) -> None:
    raise NotImplementedError


async def update_adviser_action(db, audit, action, edited: bool,
                                final_response: str | None = None) -> None:
    raise NotImplementedError
