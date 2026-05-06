import asyncio
import base64

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()

VISION_MODEL = "qwen/qwen3-vl-32b-instruct"

_VISION_PROMPT = (
    "You are parsing a page from a financial document for a RAG system.\n"
    "Extract ALL content from this page into clean markdown:\n"
    "- Preserve multi-column text: read left column top-to-bottom first, then right column\n"
    "- Render tables as markdown | tables with headers\n"
    "- For charts/graphs: describe what the chart shows, note any axis labels and data values visible\n"
    "- For KPI callout boxes: keep the number and its label on one line "
    "(e.g. \"ROTE: 14.6% (2023: 14.6%)\")\n"
    "- Output ONLY the markdown content, no preamble or commentary"
)


async def _parse_page(page_num: int, img_b64: str, client: AsyncOpenAI, semaphore: asyncio.Semaphore) -> str:
    async with semaphore:
        resp = await client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": _VISION_PROMPT},
                ],
            }],
            max_tokens=3000,
        )
        content = resp.choices[0].message.content.strip()
        logger.info("page_parsed", page=page_num + 1, chars=len(content))
        return content


async def parse_pdf_vision(file_path: str, client: AsyncOpenAI) -> str:
    """Render each PDF page as an image and extract content with a vision LLM."""
    import fitz  # lazy import — only needed for PDF path

    def _render_pages() -> list[str]:
        doc = fitz.open(file_path)
        mat = fitz.Matrix(1.5, 1.5)
        pages_b64 = []
        for page in doc:
            pix = page.get_pixmap(matrix=mat)
            pages_b64.append(base64.b64encode(pix.tobytes("png")).decode())
        doc.close()
        return pages_b64

    pages_b64 = await asyncio.to_thread(_render_pages)
    logger.info("pdf_pages_rendered", page_count=len(pages_b64))

    semaphore = asyncio.Semaphore(3)
    results = await asyncio.gather(
        *[_parse_page(i, b64, client, semaphore) for i, b64 in enumerate(pages_b64)]
    )

    return "\n\n---\n\n".join(
        f"<!-- Page {i + 1} -->\n{text}" for i, text in enumerate(results) if text.strip()
    )


def parse_docling(file_path: str) -> str:
    """Parse non-PDF files (docx, xlsx, csv) using docling."""
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(file_path)
    return result.document.export_to_markdown()
