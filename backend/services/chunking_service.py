import asyncio
import re

import structlog
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

logger = structlog.get_logger()

CHUNKING_PROMPT = (
    "You are a document chunking assistant for a financial advisory firm.\n"
    "Split the following document section into semantic chunks.\n\n"
    "Rules:\n"
    "- Each chunk should be a coherent unit of information (a section, a topic, a complete idea)\n"
    "- NEVER split a markdown table across chunks — keep entire tables in one chunk\n"
    "- Separate chunks with a line containing only ---\n"
    "- Preserve ALL content exactly — do not summarize, paraphrase, or omit anything\n"
    "- Each chunk should have a natural topic boundary\n"
    "- Do not add any commentary or metadata — only the document content with --- separators"
)

MAX_ATTEMPTS = 3
# Split input into sections of at most this many chars before sending to LLM.
# DeepSeek-chat output limit is ~4K tokens; Chinese text is ~1.5 chars/token,
# so 2000 chars in → ~1300 tokens out (well under the limit).
_SECTION_CHAR_LIMIT = 2000


def _split_into_sections(markdown: str) -> list[str]:
    """Pre-split markdown on ## headings so each piece fits in one LLM response."""
    raw_sections = re.split(r'(?=^## )', markdown, flags=re.MULTILINE)
    sections: list[str] = []
    for sec in raw_sections:
        sec = sec.strip()
        if not sec:
            continue
        # If a section is still too large, hard-split it at paragraph boundaries
        if len(sec) <= _SECTION_CHAR_LIMIT:
            sections.append(sec)
        else:
            paragraphs = re.split(r'\n{2,}', sec)
            current = ""
            for para in paragraphs:
                if current and len(current) + len(para) + 2 > _SECTION_CHAR_LIMIT:
                    sections.append(current.strip())
                    current = para
                else:
                    current = f"{current}\n\n{para}" if current else para
            if current.strip():
                sections.append(current.strip())
    return sections or [markdown]


async def _chunk_section(section: str, client: AsyncOpenAI) -> list[str]:
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": CHUNKING_PROMPT},
                    {"role": "user", "content": section},
                ],
                temperature=0.0,
            )
            raw = response.choices[0].message.content.strip()
            normalized = raw.replace("\r\n", "\n")
            parts = re.split(r'\n?^---$\n?', normalized, flags=re.MULTILINE)
            chunks = [c.strip() for c in parts if c.strip()]
            if not chunks:
                raise ValueError("LLM returned no chunks")
            return chunks
        except ValueError:
            raise
        except (APIConnectionError, RateLimitError, APIError) as e:
            last_error = e
            logger.warning("chunking_retry", attempt=attempt + 1, error=str(e))

    raise RuntimeError(f"Chunking failed after {MAX_ATTEMPTS} attempts: {last_error}")


async def chunk_document(markdown: str, client: AsyncOpenAI) -> list[str]:
    sections = _split_into_sections(markdown)
    logger.info("chunking_sections", section_count=len(sections))

    # Process sections concurrently (max 5 in-flight to avoid rate limits)
    semaphore = asyncio.Semaphore(5)

    async def _bounded(section: str) -> list[str]:
        async with semaphore:
            return await _chunk_section(section, client)

    results = await asyncio.gather(*[_bounded(s) for s in sections])
    chunks = [chunk for section_chunks in results for chunk in section_chunks]

    logger.info("chunking_complete", section_count=len(sections), chunk_count=len(chunks))
    return chunks
