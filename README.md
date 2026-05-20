# 🧳 Tempus Vestis - AI-Powered Wardrobe Consultant

> _"Time and Dress"_ - Your intelligent packing assistant for weather-based wardrobe recommendations

Tempus Vestis is an AI-powered CLI that helps you decide what to pack for any US trip. Describe your destination and timeframe in plain language; the app fetches a live weather forecast and combines it with a curated wardrobe knowledge base to return a specific, actionable packing list.

## ✨ Features

- **🤖 LangGraph Pipeline**: `StateGraph` routes through a weather agent node and a RAG node — readable, testable, and easy to extend
- **🌤️ Real-Time Weather Data**: Integration with the National Weather Service API (US locations)
- **📚 Persistent Knowledge Base**: FAISS vectorstore built once from `data/wardrobe_rules.txt` and reloaded on subsequent runs — no re-embedding cost
- **🔍 Semantic Retrieval**: `RecursiveCharacterTextSplitter` with chunk overlap feeds relevant wardrobe guidelines into each recommendation
- **💬 Natural Language Interface**: Plain-English queries — no commands or flags

## 🏗️ Architecture

### Pipeline

```
User Query
    │
    ▼
weather_agent_node  ──(error)──▶  error_node  ──▶  END
    │                                                │
    ▼                                                │
 rag_node  ──────────────────────────────────────▶  END
```

**`weather_agent_node`** — a `langchain.agents.create_agent` tool-calling agent that calls `calculate_future_date` and `get_weather_forecast` in sequence, then writes the forecast data to graph state.

**`rag_node`** — loads the FAISS vectorstore, retrieves the `k=4` most relevant wardrobe chunks, and generates a recommendation via `gpt-4o-mini`.

**`error_node`** — surfaces a clean, user-facing message when weather data cannot be retrieved (e.g. non-US location, invalid coordinates).

### Components

| Layer | Module | Responsibility |
|---|---|---|
| Pipeline | `src/core/graph.py` | LangGraph `StateGraph`, routing logic |
| Agent | `src/core/agent.py` | Tool-calling agent, message parsing |
| RAG | `src/core/rag.py` | Vectorstore, retrieval chain |
| Tools | `src/tools/` | `get_weather_forecast`, `calculate_future_date`, `get_current_date` |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key

### Installation

**With uv (recommended):**

```bash
git clone https://github.com/yourusername/tempus-vestis.git
cd tempus-vestis
uv sync
```

**With pipenv:**

```bash
git clone https://github.com/yourusername/tempus-vestis.git
cd tempus-vestis
pipenv install
```

### Set up environment variables

Create a `.env` file in the project root:

```text
OPENAI_API_KEY=your_openai_api_key_here
```

### Run the application

**With uv:**

```bash
uv run python main.py
```

**With pipenv:**

```bash
pipenv run python main.py
```

## 💡 Usage

### Interactive Mode

```bash
uv run python main.py
# or: pipenv run python main.py
```

Example queries:

- "What should I pack for Chicago in 7 days?"
- "I'm going to Miami next weekend, what should I wear?"
- "Help me pack for San Francisco 10 days from now"

### Single Query Mode

```bash
uv run python main.py "What should I pack for New York in 5 days?"
```

## 🧪 Testing

**With uv:**

```bash
uv run pytest
```

**With pipenv:**

```bash
pipenv run python -m pytest
```

## 🔧 Technical Details

### Tools

| Tool | Signature | Description |
|---|---|---|
| `get_current_date` | `() → str` | Returns today's date (YYYY-MM-DD) |
| `calculate_future_date` | `(days: int) → str` | Returns date N days from today |
| `get_weather_forecast` | `(latitude: float, longitude: float) → dict` | NWS forecast; validates coordinate ranges; retries up to 3× on network errors |

### RAG System

- **Embeddings**: OpenAI `text-embedding-3-small`
- **Vector Store**: FAISS — persisted to `data/vectorstore/` after the first run
- **Chunking**: `RecursiveCharacterTextSplitter` (chunk size 500, overlap 100)
- **Retrieval**: top-4 chunks per query (`RETRIEVAL_K = 4`)
- **Knowledge Base**: `data/wardrobe_rules.txt` — covers temperature ranges, weather conditions, activity types, and packing strategies

### Dependency Management

The project uses `pyproject.toml` as the single source of truth for package metadata and dependencies. `uv.lock` pins exact versions for reproducible installs. `Pipfile` is kept for backwards compatibility.

## 🌐 API Limitations

The National Weather Service API covers **US locations only**. Queries for non-US destinations are caught by the error node and surface a helpful message.

## 🤝 Contributing

This is a portfolio project demonstrating:

- LangGraph agent orchestration
- Tool-first AI architecture
- RAG implementation with vectorstore persistence
- Test-driven development

## 📄 License

This project is for portfolio and educational purposes.

## 🙏 Acknowledgments

- **LangChain / LangGraph**: For the agent and graph frameworks
- **National Weather Service**: For the free weather API
- **OpenAI**: For GPT-4o-mini and embeddings models

---

_Built with ❤️ using LangGraph, LangChain, OpenAI, and Python_
