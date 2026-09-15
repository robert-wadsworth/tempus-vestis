"""Integration eval for the graph's error path with a real, unmocked failure.

tests/core/test_graph.py already covers `_route_after_weather` with `run_agent`
and `WardrobeRAG` mocked out — that's a routing unit test. This eval instead
drives `build_wardrobe_graph()` end-to-end with a real agent, a real
tool-calling LLM, and a real National Weather Service API call, using a query
the NWS API is known to reject (a non-US destination), to check that the whole
pipeline actually fails gracefully in practice rather than hallucinating a
recommendation from bad or missing weather data.

The failure path is exercised by a real 404 from the NWS API, so `_get_forecast_url`'s
retry/backoff runs its full 3 attempts before giving up — this test is slower
than the others (several seconds).

Marked `eval` so it's excluded by default (see pyproject.toml addopts) and run
explicitly with `pytest -m eval`.
"""

import os

import pytest

from core.graph import build_wardrobe_graph
from core.prompts import WEATHER_ERROR_MESSAGE

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY"),
]


def test_non_us_destination_routes_to_error_node():
    graph = build_wardrobe_graph()

    result = graph.invoke({
        "query": "What should I pack for a trip to Paris, France next week?",
        "weather_data": None,
        "recommendations": None,
        "error": None,
    })

    assert result["recommendations"] == WEATHER_ERROR_MESSAGE
    assert result["error"] is not None
