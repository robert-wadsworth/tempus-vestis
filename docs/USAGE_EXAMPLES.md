# TempusVestis Usage Examples

This document provides example interactions with the TempusVestis AI Wardrobe Consultant.

## Basic Usage

### Example 1: Simple Future Trip

**Query:**

```text
What should I pack for Chicago in 7 days?
```

**Pipeline flow:**

1. `weather_agent_node` calls `calculate_future_date(days=7)` to get the target date
2. `weather_agent_node` calls `get_weather_forecast(41.8781, -87.6298)` for Chicago
3. `rag_node` retrieves relevant wardrobe chunks and generates recommendations

**Sample response:**

```text
Based on the weather forecast for Chicago...

**Destination & Dates**: Chicago, IL - [Date Range]

**Weather Summary**: Temperatures ranging from 45-60°F with partly cloudy conditions

**Packing Recommendations**:

Clothing:
- 2-3 long-sleeve shirts or light sweaters
- 1-2 t-shirts for layering
- 2 pairs of jeans or pants
- 1 light jacket or cardigan
- 1 medium-weight jacket for evenings

Footwear:
- Comfortable walking shoes
- Sneakers or boots

Accessories:
- Light scarf
- Sunglasses
- Small umbrella

**Additional Tips**:
Layering is key in Chicago - temperatures can vary throughout the day.
```

### Example 2: Weekend Beach Trip

**Query:**

```text
I'm going to Miami this weekend, what should I wear?
```

**Pipeline flow:**

1. `weather_agent_node` interprets "this weekend" and calls `calculate_future_date(days=5)`
2. `weather_agent_node` calls `get_weather_forecast(25.7617, -80.1918)` for Miami
3. `rag_node` retrieves warm-weather and beach-specific wardrobe guidelines

### Example 3: Business Trip

**Query:**

```text
Help me pack for a business trip to New York in 10 days
```

**Pipeline flow:**

1. `weather_agent_node` calls `calculate_future_date(days=10)`
2. `weather_agent_node` calls `get_weather_forecast(40.7128, -74.0060)` for New York
3. `rag_node` returns business-appropriate recommendations with weather context

## Edge Cases

### Example 4: Missing Location

**Query:**

```text
What should I pack for next week?
```

The agent can calculate the date but has no location to look up coordinates for. It will ask for the destination before proceeding.

### Example 5: Non-US Location

**Query:**

```text
What should I wear in Paris next Monday?
```

**Response:**

```text
I wasn't able to retrieve the weather forecast for that location.

This usually happens when the destination is outside the United States — the
weather service I use (National Weather Service) only covers US locations.

Could you try again with a specific US city?
```

### Example 6: Short Notice

**Query:**

```text
What should I pack for San Francisco tomorrow?
```

**Pipeline flow:**

1. `weather_agent_node` calls `calculate_future_date(days=1)`
2. `weather_agent_node` calls `get_weather_forecast(37.7749, -122.4194)` for SF
3. `rag_node` returns a compact packing list appropriate for a short trip

## Interactive Mode Examples

### Full Conversation

```text
╔══════════════════════════════════════════════════════════╗
║                     TEMPUS VESTIS                        ║
║            AI-Powered Wardrobe Consultant                ║
╚══════════════════════════════════════════════════════════╝

USAGE:
  Simply describe your travel plans, and I'll help you pack!

============================================================

💬 You: What should I pack for Seattle in 5 days?

🤖 TempusVestis:
🔍 Analyzing your request...
🌤️  Weather data retrieved successfully
📚 Consulting wardrobe knowledge base...

**Destination & Dates**: Seattle, WA - [Date Range]

**Weather Summary**: Pacific Northwest weather — expect possible rain with
temperatures between 50-65°F.

**Packing Recommendations**:

Essential Items:
- Waterproof rain jacket (absolute must!)
- 3-4 long-sleeve shirts
- 2 pairs of pants/jeans
- 1 fleece or light sweater for layering
- Waterproof or water-resistant shoes
- Umbrella (compact, travel-size)

Layers:
- Light cardigan or hoodie
- Base layers (moisture-wicking)

Accessories:
- Scarf (light)
- Sunglasses (for the occasional sunny break)

**Additional Tips**:
Seattle's weather can be unpredictable. Moisture-wicking fabrics and good
layering matter more than a heavy coat. Waterproof footwear is essential.

============================================================

💬 You: quit

👋 Thanks for using TempusVestis! Safe travels!
```

## Command-Line Single Query

```bash
$ uv run python main.py "What should I pack for Boston in 14 days?"

╔══════════════════════════════════════════════════════════╗
║                     TEMPUS VESTIS                        ║
║            AI-Powered Wardrobe Consultant                ║
╚══════════════════════════════════════════════════════════╝

💬 Query: What should I pack for Boston in 14 days?

🤖 TempusVestis:
🔍 Analyzing your request...
🌤️  Weather data retrieved successfully
📚 Consulting wardrobe knowledge base...

[Detailed recommendations follow...]
```

## Tips for Best Results

1. **Be Specific**: Include both location and timeframe

   - Good: "Chicago in 7 days"
   - Less good: "What should I pack?"

2. **US Locations Only**: The National Weather Service API covers only US destinations

3. **Reasonable Timeframes**: Weather forecasts are most accurate within the next 7-10 days

4. **Context Helps**: Mentioning the trip purpose improves recommendations

   - "Business trip to NYC"
   - "Beach vacation in Miami"
   - "Hiking in Colorado"

## Troubleshooting

### "I wasn't able to retrieve the weather forecast"

- Confirm the destination is within the United States
- Try being more specific: city and state rather than just a region

### Unexpected or generic recommendations

- Weather forecasts can shift — check the weather summary in the response
- The knowledge base is conservative and suggests being prepared for variable conditions
