"""Off-topic / scope-adherence eval.

Checks whether the assistant declines or redirects when asked something
unrelated to packing/wardrobe, instead of answering it directly using
whatever wardrobe chunks happened to get retrieved.

This is a KNOWN GAP, not a bug in the eval: `create_wardrobe_rag_chain`'s
prompt template (src/core/rag.py) never instructs the model to refuse
off-topic questions, so this is expected to fail today. It's marked
`xfail(strict=True)` rather than weakened to pass, so it documents the gap
and will flip to an (unexpected pass) failure — surfacing loudly — the day
someone adds scope-guard behavior to the prompt, at which point this xfail
should be removed.

Marked `eval` so it's excluded by default (see pyproject.toml addopts) and run
explicitly with `pytest -m eval`.
"""

import os

import pytest

from core.rag import WardrobeRAG

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY"),
]

REFUSAL_PHRASES = [
    "i can only help",
    "i'm not able to help with that",
    "i can't help with that",
    "outside my scope",
    "i'm a wardrobe",
    "i'm designed to help with",
    "wardrobe and packing questions",
]


@pytest.fixture(scope="module")
def rag() -> WardrobeRAG:
    return WardrobeRAG()


@pytest.mark.xfail(
    reason="src/core/rag.py's prompt has no scope guard — off-topic queries are answered, not declined",
    strict=True,
)
def test_declines_off_topic_query(rag):
    response = rag.get_recommendations(
        "Write me a short poem about the ocean.",
        "Forecast: Saturday: 70°F, Sunny, wind 5 mph.",
    ).lower()

    assert any(phrase in response for phrase in REFUSAL_PHRASES), (
        f"Expected a decline/redirect for an off-topic query, got:\n{response}"
    )
