import asyncio
import re

import structlog
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

logger = structlog.get_logger()

CHUNKING_PROMPT = (
    "You are a document chunking assistant for a financial advisory firm.\n"
    "Split the CURRENT PAGE CONTENT into semantic chunks.\n\n"
    "Rules:\n"
    "- Each chunk should be a coherent unit of information (a section, a topic, a complete idea)\n"
    "- NEVER split a markdown table across chunks — keep entire tables in one chunk\n"
    "- Separate chunks with a line containing only ---\n"
    "- Preserve ALL content from the current page exactly — do not summarize, paraphrase, or omit anything\n"
    "- Each chunk should have a natural topic boundary\n"
    "- Do not add any commentary or metadata — only the document content with --- separators\n"
    "- The [PREVIOUS PAGE CONTEXT] block is provided only to help you understand sentences that "
    "continue from the previous page. Do NOT include it in your output."
)

MAX_ATTEMPTS = 3
OVERLAP_CHARS = 500  # trailing chars from previous page sent as context
MAX_CONCURRENT = 5   # max parallel DeepSeek calls


def _split_pages(markdown: str) -> list[str]:
    """Split vision-parser output on <!-- Page N --> markers into per-page strings."""
    # Split on the page comment markers, keeping content between them
    parts = re.split(r'<!--\s*Page\s+\d+\s*-->', markdown)
    # Also handle the --- separators the vision parser inserts between pages
    pages = []
    for part in parts:
        # Strip the --- separators at boundaries
        cleaned = re.sub(r'^\s*---\s*\n?', '', part.strip())
        cleaned = re.sub(r'\n?\s*---\s*$', '', cleaned.strip())
        if cleaned:
            pages.append(cleaned)
    return pages or [markdown]


async def _chunk_page(
    page_text: str,
    prev_tail: str,
    client: AsyncOpenAI,
    semaphore: asyncio.Semaphore,
) -> list[str]:
    """Chunk a single page, with optional overlap context from the previous page."""
    if prev_tail:
        user_content = (
            f"[PREVIOUS PAGE CONTEXT — do not include in output]\n"
            f"{prev_tail}\n"
            f"[END PREVIOUS PAGE CONTEXT]\n\n"
            f"[CURRENT PAGE CONTENT]\n"
            f"{page_text}"
        )
    else:
        user_content = page_text

    last_error = None
    async with semaphore:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=[
                        {"role": "system", "content": CHUNKING_PROMPT},
                        {"role": "user", "content": user_content},
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
    pages = _split_pages(markdown)
    logger.info("chunking_pages", page_count=len(pages))

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # Build (page_text, prev_tail) pairs — each page gets the last OVERLAP_CHARS
    # of the previous page as context so cross-page sentences are not lost
    tasks = []
    for i, page in enumerate(pages):
        prev_tail = pages[i - 1][-OVERLAP_CHARS:] if i > 0 else ""
        tasks.append(_chunk_page(page, prev_tail, client, semaphore))

    results = await asyncio.gather(*tasks)
    chunks = [chunk for page_chunks in results for chunk in page_chunks]

    logger.info("chunking_complete", page_count=len(pages), chunk_count=len(chunks))
    return chunks
