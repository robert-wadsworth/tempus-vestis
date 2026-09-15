"""LLM-as-judge eval for the end-to-end wardrobe recommendation chain.

The keyword eval (test_recommendation_eval.py) is fast and cheap but brittle —
it flagged the model for mentioning "sandals" as a secondary camp shoe next to
insulated boots, which is reasonable advice, not a wrong answer. This eval
uses a second LLM call to judge the same kind of question a human reviewer
would ask: is this recommendation actually appropriate for the weather, not
just "does it contain these exact words." That judgment call costs an extra
chat-completion call per case and inherits its own non-determinism, so it's
meant to complement the keyword eval, not replace it — run occasionally
(e.g. after a prompt or model change), not on every commit.

Marked `eval` so it's excluded by default (see pyproject.toml addopts) and run
explicitly with `pytest -m eval`.
"""

import json
import os

import pytest
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

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

JUDGE_RUBRIC = """You are grading a wardrobe-packing assistant's response for quality.

User query: {query}
Weather forecast given to the assistant: {weather_info}

Assistant's recommendation:
---
{recommendation}
---

Judge the recommendation against these criteria:
1. It recommends primary clothing/gear that is genuinely appropriate for the stated weather.
2. It is specific and actionable (a real packing list), not vague or generic filler.
3. It does not recommend anything that would be unsafe or clearly wrong as PRIMARY attire
   for the conditions. Mentioning an item as a secondary/optional choice (e.g. camp shoes
   listed alongside insulated boots) is fine and should NOT count against it.

Respond with ONLY a JSON object, no markdown fences, in this exact shape:
{{"pass": true or false, "reason": "one sentence explaining the verdict"}}"""


def _build_judge():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    prompt = ChatPromptTemplate.from_template(JUDGE_RUBRIC)
    return prompt | llm | StrOutputParser()


@pytest.fixture(scope="module")
def rag() -> WardrobeRAG:
    return WardrobeRAG()


@pytest.fixture(scope="module")
def judge():
    return _build_judge()


@pytest.mark.parametrize(
    "query, weather_info",
    [
        pytest.param(*COLD_SNOWY_WEEKEND, id="cold_snowy_weekend"),
        pytest.param(*HOT_SUNNY_BEACH, id="hot_sunny_beach"),
        pytest.param(*MID_RANGE_RAINY, id="mid_range_rainy"),
        pytest.param(*BUSINESS_TRIP, id="business_trip"),
    ],
)
def test_recommendation_passes_judge(rag, judge, query, weather_info):
    recommendation = rag.get_recommendations(query, weather_info)

    verdict_raw = judge.invoke(
        {"query": query, "weather_info": weather_info, "recommendation": recommendation}
    )
    verdict = json.loads(verdict_raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```"))

    assert verdict["pass"], (
        f"Judge rejected recommendation for {query!r} given {weather_info!r}: "
        f"{verdict['reason']}\n\nRecommendation was:\n{recommendation}"
    )
