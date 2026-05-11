"""Unit tests for chunk metadata extraction (Phase 7 — META-01)."""
import pytest
from unittest.mock import MagicMock


def _make_mock_client(chunks_per_page: list[list[str]]):
    """Return an AsyncOpenAI mock that returns chunks for each page call."""
    call_count = 0
    responses = []
    for page_chunks in chunks_per_page:
        content = "\n---\n".join(page_chunks)
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = content
        responses.append(mock_resp)

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()

    async def _create(**kwargs):
        nonlocal call_count
        resp = responses[call_count % len(responses)]
        call_count += 1
        return resp

    client.chat.completions.create = _create
    return client


@pytest.mark.asyncio
async def test_chunk_document_returns_dicts():
    """chunk_document() returns list[dict] with required keys."""
    from backend.services.chunking_service import chunk_document
    markdown = "<!-- Page 1 -->\n## Introduction\nSome text here."
    client = _make_mock_client([["Some text here."]])
    result = await chunk_document(markdown, client)
    assert isinstance(result, list)
    assert len(result) > 0
    chunk = result[0]
    for key in ("text", "page_number", "section_heading", "is_table", "is_figure",
                "chunk_position", "total_chunks_in_doc"):
        assert key in chunk, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_page_number_is_1_indexed():
    """page_number starts at 1 for the first page."""
    from backend.services.chunking_service import chunk_document
    markdown = "<!-- Page 1 -->\nContent page one.\n<!-- Page 2 -->\nContent page two."
    client = _make_mock_client([["Content page one."], ["Content page two."]])
    result = await chunk_document(markdown, client)
    page_numbers = [c["page_number"] for c in result]
    assert 1 in page_numbers
    assert 2 in page_numbers


@pytest.mark.asyncio
async def test_chunk_position_single_chunk():
    """Single chunk gets chunk_position='first' (also last — use 'first')."""
    from backend.services.chunking_service import chunk_document
    markdown = "<!-- Page 1 -->\nOnly chunk."
    client = _make_mock_client([["Only chunk."]])
    result = await chunk_document(markdown, client)
    assert len(result) == 1
    assert result[0]["chunk_position"] == "first"
    assert result[0]["total_chunks_in_doc"] == 1


@pytest.mark.asyncio
async def test_chunk_position_multiple_chunks():
    """First/middle/last positions assigned correctly."""
    from backend.services.chunking_service import chunk_document
    markdown = "<!-- Page 1 -->\nA\n<!-- Page 2 -->\nB\n<!-- Page 3 -->\nC"
    client = _make_mock_client([["A"], ["B"], ["C"]])
    result = await chunk_document(markdown, client)
    assert result[0]["chunk_position"] == "first"
    assert result[-1]["chunk_position"] == "last"
    if len(result) > 2:
        assert result[1]["chunk_position"] == "middle"


@pytest.mark.asyncio
async def test_is_table_detection():
    """is_table=True when chunk contains markdown table."""
    from backend.services.chunking_service import chunk_document
    table_chunk = "| Col1 | Col2 |\n|------|------|\n| A | B |"
    markdown = f"<!-- Page 1 -->\n{table_chunk}"
    client = _make_mock_client([[table_chunk]])
    result = await chunk_document(markdown, client)
    assert result[0]["is_table"] is True


@pytest.mark.asyncio
async def test_is_figure_detection():
    """is_figure=True when chunk starts with Figure/Chart/Graph."""
    from backend.services.chunking_service import chunk_document
    figure_chunk = "Figure: Revenue growth 2020-2024 showing 15% CAGR."
    markdown = f"<!-- Page 1 -->\n{figure_chunk}"
    client = _make_mock_client([[figure_chunk]])
    result = await chunk_document(markdown, client)
    assert result[0]["is_figure"] is True


@pytest.mark.asyncio
async def test_section_heading_extracted():
    """section_heading captures the last heading before the chunk."""
    from backend.services.chunking_service import chunk_document
    markdown = "<!-- Page 1 -->\n## Revenue\nRevenue was $100M."
    client = _make_mock_client([["Revenue was $100M."]])
    result = await chunk_document(markdown, client)
    assert result[0]["section_heading"] == "Revenue"
