# TempusVestis Usage Examples

This document provides example interactions with the TempusVestis AI Wardrobe Consultant.

## Basic Usage

### Example 1: Simple Future Trip

**Query:**

```text
What should I pack for Chicago in 7 days?
```

**Expected Flow:**

1. `weather_agent_node` calls `calculate_future_date(days=7)` then `get_weather_forecast` for Chicago
2. `rag_node` retrieves relevant wardrobe chunks and generates recommendations

**Sample Response:**

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
- Light scarf (functional and fashionable)
- Sunglasses
- Small umbrella (just in case)

**Additional Tips**:
Layering is key in Chicago - temperatures can vary throughout the day. The "windy city"
nickname is earned, so a windbreaker is recommended!
```

### Example 2: Weekend Beach Trip

**Query:**

```text
I'm going to Miami this weekend, what should I wear?
```

**Expected Flow:**

1. `weather_agent_node` calls `calculate_future_date` for the weekend date then `get_weather_forecast` for Miami
2. `rag_node` retrieves warm-weather and beach-relevant wardrobe chunks and generates recommendations

### Example 3: Business Trip

**Query:**

```text
Help me pack for a business trip to New York in 10 days
```

**Expected Flow:**

1. `weather_agent_node` calls `calculate_future_date(days=10)` then `get_weather_forecast` for New York
2. `rag_node` retrieves business/professional wardrobe chunks and generates recommendations

## Edge Cases

### Example 4: Ambiguous Location

**Query:**

```text
What should I pack for next week?
```

**Expected Response:**

The agent will ask for the missing destination before attempting to retrieve a forecast.

### Example 5: Non-US Location

**Query:**

```text
What should I wear in Paris next Monday?
```

**Expected Response:**

```text
I wasn't able to retrieve the weather forecast for that location.

This usually happens when the destination is outside the United States — the weather service I use (National Weather Service) only covers US locations.

Could you try again with a specific US city?
```

### Example 6: Very Short Notice

**Query:**

```text
What should I pack for San Francisco tomorrow?
```

**Expected Flow:**

1. `weather_agent_node` calls `calculate_future_date(days=1)` then `get_weather_forecast` for San Francisco
2. `rag_node` retrieves SF-relevant wardrobe chunks (noting its unique microclimate) and generates recommendations

## Interactive Mode Examples

### Full Conversation Example

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

**Weather Summary**: Pacific Northwest weather - expect possible rain with
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
- Sunglasses (for those moments when it's not raining!)

**Additional Tips**:
Seattle's weather can be unpredictable. The key is moisture-wicking fabrics and
good layering. Don't overdress - locals rarely use umbrellas but having one won't
hurt! Waterproof footwear is more important than you think.

============================================================

💬 You: What if it's colder than expected?

🤖 TempusVestis:
Great question! If temperatures drop below the forecast, here's what you should add:

- An additional mid-weight fleece or insulated vest
- Warm hat (can pack a lightweight beanie)
- Light gloves
- Thermal undershirt for extra layering

The beauty of layering is flexibility - you can always add or remove as needed!

============================================================

💬 You: quit

👋 Thanks for using TempusVestis! Safe travels!
```

## Command-Line Single Query

### Example Usage

```bash
$ python main.py "What should I pack for Boston in 14 days?"

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

3. **Reasonable Timeframes**: Weather forecasts are most accurate for the next 7-10 days

4. **Context Helps**: Mention trip purpose if relevant

   - "Business trip to NYC"
   - "Beach vacation in Miami"
   - "Hiking in Colorado"

5. **Follow-up Questions**: Feel free to ask for clarification or modifications

## Troubleshooting

### "I encountered an error" messages

- Check your OpenAI API key is set correctly in `.env`
- Ensure the location is in the United States
- Try being more specific with the location (city and state)

### "I need more specific information"

- Provide both a location and a timeframe
- Use specific dates or "X days from now"

### Unexpected recommendations

- Weather forecasts can change - check the weather summary in the response
- The RAG system is conservative and suggests being prepared for various conditions
