"""
Agent implementation for TempusVestis.

Creates a LangGraph-backed tool-calling agent that retrieves weather data
and date information before handing control to the RAG pipeline.
"""

import ast
import json
import os
from typing import Any, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from core.prompts import WARDROBE_CONSULTANT_SYSTEM_PROMPT
from tools.date_ops import calculate_future_date, get_current_date
from tools.weather_api import get_weather_forecast

_TOOLS = [get_current_date, calculate_future_date, get_weather_forecast]


def create_wardrobe_agent(
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.7,
):
    """Return a compiled LangGraph agent wired with the wardrobe tools."""
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    return create_agent(llm, _TOOLS, system_prompt=WARDROBE_CONSULTANT_SYSTEM_PROMPT)


def _parse_tool_content(content: str) -> Any:
    """Parse a tool output string, returning a dict when possible."""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        return ast.literal_eval(content)
    except (ValueError, SyntaxError):
        pass
    return content


def run_agent(
    query: str,
    agent: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Run the wardrobe agent and extract weather data from tool messages.

    Returns a dict with keys:
      - weather_data: parsed dict from the get_weather_forecast tool, or None
      - output: the agent's final text response
      - messages: full message list from the graph run
    """
    if agent is None:
        agent = create_wardrobe_agent()

    result = agent.invoke({"messages": [HumanMessage(content=query)]})

    weather_data: Optional[Any] = None
    final_output: str = ""

    for msg in result["messages"]:
        if isinstance(msg, ToolMessage) and msg.name == "get_weather_forecast":
            weather_data = _parse_tool_content(msg.content)
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            final_output = msg.content

    return {
        "weather_data": weather_data,
        "output": final_output,
        "messages": result["messages"],
    }


class WardrobeAgent:
    """Thin wrapper around run_agent for callers that want an object interface."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        verbose: bool = False,
    ) -> None:
        self._agent = create_wardrobe_agent(model_name=model_name, temperature=temperature)

    def ask(self, query: str) -> str:
        """Return the agent's final text response."""
        return run_agent(query, self._agent)["output"]

    def get_detailed_response(self, query: str) -> dict[str, Any]:
        """Return the full run_agent result dict."""
        return run_agent(query, self._agent)
