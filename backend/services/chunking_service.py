import re

import structlog
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

logger = structlog.get_logger()

CHUNKING_PROMPT = (
    "You are a document chunking assistant for a financial advisory firm.\n"
    "Split the following document into semantic chunks.\n\n"
    "Rules:\n"
    "- Each chunk should be a coherent unit of information (a section, a topic, a complete idea)\n"
    "- NEVER split a markdown table across chunks — keep entire tables in one chunk\n"
    "- Separate chunks with a line containing only ---\n"
    "- Preserve ALL content exactly — do not summarize, paraphrase, or omit anything\n"
    "- Each chunk should have a natural topic boundary\n"
    "- Do not add any commentary or metadata — only the document content with --- separators"
)

MAX_ATTEMPTS = 3


async def chunk_document(markdown: str, client: AsyncOpenAI) -> list[str]:
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": CHUNKING_PROMPT},
                    {"role": "user", "content": markdown},
                ],
                temperature=0.0,
            )
            raw = response.choices[0].message.content.strip()
            normalized = raw.replace("\r\n", "\n")
            parts = re.split(r'\n?^---$\n?', normalized, flags=re.MULTILINE)
            chunks = [c.strip() for c in parts if c.strip()]
            if not chunks:
                raise ValueError("LLM returned no chunks")
            logger.info("chunking_complete", chunk_count=len(chunks))
            return chunks
        except ValueError:
            raise
        except (APIConnectionError, RateLimitError, APIError) as e:
            last_error = e
            logger.warning("chunking_retry", attempt=attempt + 1, error=str(e))

    raise RuntimeError(f"Chunking failed after {MAX_ATTEMPTS} attempts: {last_error}")
