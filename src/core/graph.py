"""
LangGraph pipeline for TempusVestis.

Defines the WardrobeState and a two-node graph:
  START → weather_agent_node → rag_node → END
                    ↓ (on error)
             error_node → END
"""

from typing import Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from core.agent import run_agent
from core.prompts import WEATHER_ERROR_MESSAGE
from core.rag import WardrobeRAG


class WardrobeState(TypedDict):
    query: str
    weather_data: Optional[dict]
    recommendations: Optional[str]
    error: Optional[str]


def weather_agent_node(state: WardrobeState) -> WardrobeState:
    try:
        result = run_agent(state["query"])
        if result["weather_data"] is None:
            return {**state, "error": "No weather data could be retrieved for the requested location."}
        return {**state, "weather_data": result["weather_data"]}
    except Exception as exc:
        return {**state, "error": str(exc)}


def rag_node(state: WardrobeState) -> WardrobeState:
    rag = WardrobeRAG()
    recommendations = rag.get_recommendations(state["query"], state["weather_data"])
    return {**state, "recommendations": recommendations}


def error_node(state: WardrobeState) -> WardrobeState:
    return {**state, "recommendations": WEATHER_ERROR_MESSAGE}


def _route_after_weather(state: WardrobeState) -> str:
    return "error_node" if state.get("error") else "rag_node"


def build_wardrobe_graph():
    """Compile and return the wardrobe recommendation graph."""
    graph: StateGraph = StateGraph(WardrobeState)

    graph.add_node("weather_agent_node", weather_agent_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("error_node", error_node)

    graph.add_edge(START, "weather_agent_node")
    graph.add_conditional_edges(
        "weather_agent_node",
        _route_after_weather,
        {"rag_node": "rag_node", "error_node": "error_node"},
    )
    graph.add_edge("rag_node", END)
    graph.add_edge("error_node", END)

    return graph.compile()
