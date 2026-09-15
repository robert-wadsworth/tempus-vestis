"""Retrieval relevance eval.

Unlike tests/core/test_rag.py, this hits the real embeddings API and the real
FAISS index in data/vectorstore — no mocks — to check that retrieval actually
surfaces relevant wardrobe guidance for a query, not just that the retrieval
call wires together correctly.

Marked `eval` so it's excluded by default (see pyproject.toml addopts) and run
explicitly with `pytest -m eval`, since it costs real embedding-API calls.
"""

import os

import pytest

from core.rag import WardrobeRAG

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY"),
]

RETRIEVAL_CASES = [
    pytest.param(
        "What should I pack for rainy weather?",
        ["waterproof", "rain jacket", "umbrella", "raincoat"],
        id="rainy",
    ),
    pytest.param(
        "Packing for a hot beach vacation",
        ["sunscreen", "sandals", "swimwear", "breathable"],
        id="hot_beach",
    ),
    pytest.param(
        "What do I need for a cold snowy trip?",
        ["insulated", "winter coat", "gloves", "boots"],
        id="cold_snow",
    ),
    pytest.param(
        "What should I wear to a business conference?",
        ["suit", "dress shirt", "blazer", "professional", "dress shoes", "blouse"],
        id="business",
    ),
]


@pytest.fixture(scope="module")
def rag() -> WardrobeRAG:
    return WardrobeRAG()


@pytest.mark.parametrize("query, expected_keywords", RETRIEVAL_CASES)
def test_retrieval_surfaces_relevant_guidance(rag, query, expected_keywords):
    docs = rag.search_knowledge(query, k=4)
    combined = " ".join(doc.page_content for doc in docs).lower()

    assert any(keyword in combined for keyword in expected_keywords), (
        f"Expected one of {expected_keywords} in retrieved chunks for query "
        f"{query!r}, got:\n{combined}"
    )
