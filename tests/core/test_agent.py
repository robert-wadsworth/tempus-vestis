import pytest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from core.agent import _parse_tool_content, run_agent


class TestParseToolContent:
    def test_parses_json_string(self):
        result = _parse_tool_content('{"temperature": 72, "forecast": "Sunny"}')
        assert result == {"temperature": 72, "forecast": "Sunny"}

    def test_parses_python_literal(self):
        result = _parse_tool_content("{'temperature': 72, 'forecast': 'Sunny'}")
        assert result == {"temperature": 72, "forecast": "Sunny"}

    def test_returns_string_when_not_parseable(self):
        result = _parse_tool_content("plain text output")
        assert result == "plain text output"

    def test_handles_nested_dict(self):
        result = _parse_tool_content('{"properties": {"periods": [{"name": "Today"}]}}')
        assert result["properties"]["periods"][0]["name"] == "Today"


class TestRunAgent:
    def _make_agent(self, messages: list) -> MagicMock:
        agent = MagicMock()
        agent.invoke.return_value = {"messages": messages}
        return agent

    def test_extracts_weather_data_from_tool_message(self):
        weather_payload = '{"properties": {"periods": [{"name": "Today", "temperature": 75}]}}'
        messages = [
            HumanMessage(content="What should I pack for Chicago?"),
            ToolMessage(content=weather_payload, name="get_weather_forecast", tool_call_id="1"),
            AIMessage(content="Here are your recommendations."),
        ]
        result = run_agent("What should I pack for Chicago?", agent=self._make_agent(messages))

        assert result["weather_data"] is not None
        assert result["weather_data"]["properties"]["periods"][0]["temperature"] == 75

    def test_weather_data_is_none_when_no_tool_message(self):
        messages = [
            HumanMessage(content="query"),
            AIMessage(content="Final response."),
        ]
        result = run_agent("query", agent=self._make_agent(messages))
        assert result["weather_data"] is None

    def test_returns_final_ai_message_as_output(self):
        messages = [
            HumanMessage(content="query"),
            AIMessage(content="Pack a raincoat."),
        ]
        result = run_agent("query", agent=self._make_agent(messages))
        assert result["output"] == "Pack a raincoat."

    def test_ignores_ai_messages_with_tool_calls(self):
        tool_call_msg = AIMessage(content="", tool_calls=[{"name": "get_weather_forecast", "args": {}, "id": "1"}])
        final_msg = AIMessage(content="Pack light layers.")
        messages = [
            HumanMessage(content="query"),
            tool_call_msg,
            ToolMessage(content="{}", name="get_weather_forecast", tool_call_id="1"),
            final_msg,
        ]
        result = run_agent("query", agent=self._make_agent(messages))
        assert result["output"] == "Pack light layers."

    def test_returns_all_messages(self):
        messages = [
            HumanMessage(content="query"),
            AIMessage(content="response"),
        ]
        result = run_agent("query", agent=self._make_agent(messages))
        assert result["messages"] == messages
