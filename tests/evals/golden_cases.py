"""Shared golden (query, weather_info) pairs used by multiple evals.

Kept separate so the keyword eval and the LLM-as-judge eval score the exact
same inputs, instead of drifting apart as each file evolves independently.
"""

COLD_SNOWY_WEEKEND = (
    "What should I pack for a weekend camping trip?",
    "Forecast: Saturday: 15°F, Snow showers, wind 20 mph. Sunday: 10°F, Clear, wind 15 mph.",
)

HOT_SUNNY_BEACH = (
    "What should I pack for a weekend beach trip?",
    "Forecast: Saturday: 95°F, Sunny, wind 5 mph. Sunday: 92°F, Sunny, wind 5 mph.",
)

# Cool-and-rainy overlaps two rule sections in data/wardrobe_rules.txt (COOL
# WEATHER and RAINY CONDITIONS) — exercises whether the RAG chain blends both
# instead of only surfacing one.
MID_RANGE_RAINY = (
    "What should I pack for a weekend trip?",
    "Forecast: Saturday: 55°F, Rain showers, wind 10 mph. Sunday: 52°F, Rain, wind 15 mph.",
)

# Exercises the ACTIVITY-BASED / BUSINESS-PROFESSIONAL section of the
# knowledge base, which none of the other golden cases touch.
BUSINESS_TRIP = (
    "What should I pack for a business conference in Chicago next week?",
    "Forecast: Monday: 65°F, Partly cloudy, wind 5 mph. Tuesday: 63°F, Cloudy, wind 5 mph.",
)
