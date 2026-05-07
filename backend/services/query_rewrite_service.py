import structlog
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

logger = structlog.get_logger()

REWRITE_PROMPT = (
    "You are a financial query assistant. Rewrite the user's query to be more precise "
    "for document retrieval. Expand abbreviations, add relevant financial domain terms. "
    "Return only the rewritten query, no explanation."
)


async def rewrite_query(query: str, client: AsyncOpenAI) -> str:
    """Rewrite query via DeepSeek V4 Flash for better retrieval.

    Falls back to original query on any API error — rewrite is an enhancement,
    not a blocker.
    """
    try:
        response = await client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": REWRITE_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
        )
        rewritten = response.choices[0].message.content.strip()
        logger.info(
            "query_rewrite_complete",
            original_len=len(query),
            rewritten_len=len(rewritten),
        )
        return rewritten
    except (APIConnectionError, RateLimitError, APIError) as e:
        logger.warning("query_rewrite_fallback", error=str(e))
        return query
