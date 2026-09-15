"""Golden-output eval for the end-to-end wardrobe recommendation chain.

Unlike tests/core/test_rag.py, this makes a real call to gpt-4o-mini via
WardrobeRAG.get_recommendations() for a small set of fixed (query, weather)
cases, and checks the response for weather-appropriate keywords. LLM output
is non-deterministic, so assertions are loose (substring checks against a
list of acceptable terms) rather than exact-match.

Marked `eval` so it's excluded by default (see pyproject.toml addopts) and run
explicitly with `pytest -m eval`, since it costs real chat-completion calls.
"""

import os

import pytest

from core.rag import WardrobeRAG

from tests.evals.golden_cases import (
    BUSINESS_TRIP,
    COLD_SNOWY_WEEKEND,
    HOT_SUNNY_BEACH,
    MID_RANGE_RAINY,
)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY"),
]

RECOMMENDATION_CASES = [
    pytest.param(
        *COLD_SNOWY_WEEKEND,
        ["coat", "jacket", "gloves", "boots", "thermal", "insulated", "scarf", "hat"],
        # "sandals"/"flip-flops" deliberately excluded: models reasonably suggest
        # them as a secondary camp/slip-on shoe alongside insulated boots, not as
        # primary footwear — a legitimate answer, not a wrong one. Keyword bans
        # can't express "fine as a secondary mention" — see test_judge_eval.py,
        # which judges this distinction instead of banning words outright.
        ["swimsuit", "tank top"],
        id="cold_snowy_weekend",
    ),
    pytest.param(
        *HOT_SUNNY_BEACH,
        ["sunscreen", "shorts", "sandals", "hat", "sunglasses", "breathable", "tank top", "light"],
        ["winter coat", "gloves", "thermal underwear", "snow boots"],
        id="hot_sunny_beach",
    ),
    pytest.param(
        *MID_RANGE_RAINY,
        ["rain", "waterproof", "jacket", "layer"],
        # Footwear terms ("sandals" etc.) deliberately excluded from forbidden
        # lists after two flakes here — see the cold_snowy_weekend case above.
        ["shorts", "tank top", "swimsuit"],
        id="mid_range_rainy",
    ),
    pytest.param(
        *BUSINESS_TRIP,
        ["suit", "dress shirt", "blazer", "professional", "dress shoes", "blouse"],
        ["shorts", "tank top", "flip-flops", "swimsuit"],
        id="business_trip",
    ),
]


@pytest.fixture(scope="module")
def rag() -> WardrobeRAG:
    return WardrobeRAG()


@pytest.mark.parametrize("query, weather_info, expected_any, forbidden", RECOMMENDATION_CASES)
def test_recommendation_matches_weather(rag, query, weather_info, expected_any, forbidden):
    recommendation = rag.get_recommendations(query, weather_info).lower()

    assert any(keyword in recommendation for keyword in expected_any), (
        f"Expected one of {expected_any} in recommendation for {query!r} "
        f"given {weather_info!r}, got:\n{recommendation}"
    )
    for keyword in forbidden:
        assert keyword not in recommendation, (
            f"Did not expect {keyword!r} in recommendation for {query!r} "
            f"given {weather_info!r}, got:\n{recommendation}"
        )
