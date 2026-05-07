import re

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()

GENERATION_PROMPT = (
    "You are a compliance-aware financial assistant. Answer the user's question using ONLY "
    "the provided context chunks. For every factual claim, include an inline citation marker "
    "[N] where N is the chunk number. If the provided context is empty or does not contain "
    "sufficient information to answer the question, respond with exactly: NO_RELEVANT_CONTENT "
    "followed by a brief description of what the user was asking for. Never use your training "
    "data or external knowledge."
)


def _build_context(chunks: list) -> str:
    """Format chunks as numbered context for the LLM prompt."""
    if not chunks:
        return "(no context provided)"
    parts = []
    for i, pt in enumerate(chunks, start=1):
        doc_name = pt.payload.get("source_id", "unknown")
        section = pt.payload.get("section_title", "")
        text = pt.payload.get("text", "")
        header = f"[{i}] {doc_name}"
        if section:
            header += f" — {section}"
        parts.append(f"{header}\n{text}")
    return "\n\n".join(parts)


def _extract_sources(answer: str, chunks: list) -> list[dict]:
    """Extract cited sources from [N] markers in the answer."""
    indices = re.findall(r'\[(\d+)\]', answer)
    seen = set()
    sources = []
    for idx_str in indices:
        n = int(idx_str)
        if n < 1 or n > len(chunks):
            continue  # out-of-range — skip silently
        pt = chunks[n - 1]
        doc_name = pt.payload.get("source_id", "")
        chunk_index = pt.payload.get("chunk_index", 0)
        key = (doc_name, chunk_index)
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "doc_name": doc_name,
            "section_title": pt.payload.get("section_title", ""),
            "chunk_index": chunk_index,
        })
    return sources


async def generate_answer(query: str, chunks: list, client: AsyncOpenAI) -> dict:
    """Generate an answer with inline [N] citations using DeepSeek V4 Pro.

    client must be the generation_client (deepseek_api_key, deepseek base URL).
    Returns dict with answer, sources, not_found, model_used, prompt_tokens, completion_tokens.
    """
    context = _build_context(chunks)
    user_message = f"Context:\n{context}\n\n<user_question>{query}</user_question>"

    response = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": GENERATION_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )

    response_text = response.choices[0].message.content.strip()
    not_found = "NO_RELEVANT_CONTENT" in response_text

    if not_found:
        answer = "This information is not available in the approved documents."
        sources = []
    else:
        answer = response_text
        sources = _extract_sources(answer, chunks)

    logger.info(
        "generation_complete",
        not_found=not_found,
        source_count=len(sources),
    )

    return {
        "answer": answer,
        "sources": sources,
        "not_found": not_found,
        "model_used": "deepseek-v4-pro",
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "prompt_sent": user_message,
    }
