import pytest
from unittest.mock import MagicMock, patch

from core.graph import build_wardrobe_graph
from core.prompts import WEATHER_ERROR_MESSAGE


def _invoke(query: str, weather_data: dict | None = None, run_agent_exc: Exception | None = None) -> dict:
    """Build and invoke the graph with run_agent and WardrobeRAG mocked."""
    mock_rag = MagicMock()
    mock_rag.get_recommendations.return_value = "Bring a jacket and layers."

    def fake_run_agent(q, agent=None):
        if run_agent_exc:
            raise run_agent_exc
        return {"weather_data": weather_data, "output": "", "messages": []}

    with patch('core.graph.run_agent', side_effect=fake_run_agent):
        with patch('core.graph.WardrobeRAG', return_value=mock_rag):
            graph = build_wardrobe_graph()
            return graph.invoke({
                "query": query,
                "weather_data": None,
                "recommendations": None,
                "error": None,
            })


class TestWardrobeGraph:
    def test_produces_recommendations_on_success(self):
        weather = {"properties": {"periods": [{"name": "Today", "temperature": 70}]}}
        result = _invoke("What should I pack for Chicago?", weather_data=weather)

        assert result["recommendations"] == "Bring a jacket and layers."
        assert result["error"] is None

    def test_routes_to_error_when_weather_data_is_none(self):
        result = _invoke("What should I pack for Chicago?", weather_data=None)

        assert result["recommendations"] == WEATHER_ERROR_MESSAGE
        assert result["error"] is not None

    def test_routes_to_error_on_agent_exception(self):
        result = _invoke("query", run_agent_exc=RuntimeError("NWS API unavailable"))

        assert result["recommendations"] == WEATHER_ERROR_MESSAGE
        assert "NWS API unavailable" in result["error"]

    def test_rag_node_receives_weather_data(self):
        weather = {"properties": {"periods": []}}
        mock_rag = MagicMock()
        mock_rag.get_recommendations.return_value = "recommendations"

        with patch('core.graph.run_agent', return_value={"weather_data": weather, "output": "", "messages": []}):
            with patch('core.graph.WardrobeRAG', return_value=mock_rag):
                graph = build_wardrobe_graph()
                graph.invoke({"query": "test", "weather_data": None, "recommendations": None, "error": None})

        mock_rag.get_recommendations.assert_called_once_with("test", weather)
