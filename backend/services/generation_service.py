import re

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()

_SYSTEM_PROMPTS = {
    "brief": (
        "You are a compliance-aware financial assistant preparing a meeting brief for an investment adviser. "
        "Using ONLY the provided context chunks, produce a structured brief with these sections:\n"
        "1. Client / Topic Overview\n"
        "2. Key Holdings or Products\n"
        "3. Talking Points\n"
        "4. Risks and Considerations\n"
        "For every factual claim include an inline citation [N]. "
        "If the context is insufficient, respond with exactly: NO_RELEVANT_CONTENT followed by a brief description. "
        "Never use training data or external knowledge."
    ),
    "product": (
        "You are a compliance-aware financial assistant summarizing product information for an investment adviser. "
        "Using ONLY the provided context chunks, produce a structured summary with these sections:\n"
        "1. Product Overview\n"
        "2. Key Features and Terms\n"
        "3. Fees and Charges\n"
        "4. Suitability and Target Investors\n"
        "5. Regulatory and Compliance Notes\n"
        "For every factual claim include an inline citation [N]. "
        "If the context is insufficient, respond with exactly: NO_RELEVANT_CONTENT followed by a brief description. "
        "Never use training data or external knowledge."
    ),
    "followup": (
        "You are a compliance-aware financial assistant drafting a post-meeting follow-up note for an investment adviser. "
        "Using ONLY the provided context chunks, produce a professional follow-up note with these sections:\n"
        "1. Meeting Summary\n"
        "2. Products or Strategies Discussed\n"
        "3. Client Instructions and Action Items\n"
        "4. Required Disclosures\n"
        "5. Next Steps\n"
        "For every factual claim include an inline citation [N]. "
        "If the context is insufficient, respond with exactly: NO_RELEVANT_CONTENT followed by a brief description. "
        "Never use training data or external knowledge."
    ),
}

_DEFAULT_PROMPT = (
    "You are a compliance-aware financial assistant. Answer the user's question using ONLY "
    "the provided context chunks. For every factual claim, include an inline citation marker "
    "[N] where N is the chunk number. If the provided context is empty or does not contain "
    "sufficient information to answer the question, respond with exactly: NO_RELEVANT_CONTENT "
    "followed by a brief description of what the user was asking for. Never use your training "
    "data or external knowledge."
)


def _build_context(chunks: list) -> str:
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
    indices = re.findall(r'\[(\d+)\]', answer)
    seen = set()
    sources = []
    for idx_str in indices:
        n = int(idx_str)
        if n < 1 or n > len(chunks):
            continue
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


async def generate_answer(query: str, chunks: list, client: AsyncOpenAI, intent: str = "default") -> dict:
    """Generate a structured answer with inline [N] citations.

    intent: "brief" | "product" | "followup" | "default"
    """
    system_prompt = _SYSTEM_PROMPTS.get(intent, _DEFAULT_PROMPT)
    context = _build_context(chunks)
    user_message = f"Context:\n{context}\n\n<request>{query}</request>"

    response = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": system_prompt},
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

    logger.info("generation_complete", not_found=not_found, source_count=len(sources), intent=intent)

    return {
        "answer": answer,
        "sources": sources,
        "not_found": not_found,
        "model_used": "deepseek-v4-pro",
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "prompt_sent": user_message,
    }
