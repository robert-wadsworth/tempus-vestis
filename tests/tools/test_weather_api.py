import pytest
from unittest.mock import patch, Mock
from tools.weather_api import get_weather_forecast, _get_forecast_url
from tools.constants import NWS_BASE_URL


class TestGetForecastUrl:
    """Test suite for _get_forecast_url helper function."""

    @patch('tools.weather_api.requests.get')
    def test_returns_forecast_url(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TOP/31,80/forecast"
            }
        }
        mock_get.return_value = mock_response

        result = _get_forecast_url(39.7456, -97.0892)

        expected_url = f"{NWS_BASE_URL}/points/39.7456,-97.0892"
        mock_get.assert_called_once_with(expected_url)
        assert result == "https://api.weather.gov/gridpoints/TOP/31,80/forecast"

    @patch('tools.weather_api.requests.get')
    def test_handles_different_coordinates(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/LOX/123,456/forecast"
            }
        }
        mock_get.return_value = mock_response

        result = _get_forecast_url(34.0522, -118.2437)

        expected_url = f"{NWS_BASE_URL}/points/34.0522,-118.2437"
        mock_get.assert_called_once_with(expected_url)
        assert result == "https://api.weather.gov/gridpoints/LOX/123,456/forecast"

    @patch('tools.weather_api.requests.get')
    def test_handles_negative_coordinates(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TEST/1,2/forecast"
            }
        }
        mock_get.return_value = mock_response

        result = _get_forecast_url(-10.5, -75.3)

        expected_url = f"{NWS_BASE_URL}/points/-10.5,-75.3"
        mock_get.assert_called_once_with(expected_url)
        assert isinstance(result, str)

    @patch('tools.weather_api.requests.get')
    def test_raises_key_error_on_invalid_response(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "response"}
        mock_get.return_value = mock_response

        with pytest.raises(KeyError):
            _get_forecast_url(39.7456, -97.0892)


class TestGetWeatherForecast:
    """Test suite for get_weather_forecast tool function."""

    @patch('tools.weather_api.requests.get')
    def test_returns_forecast(self, mock_get):
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TOP/31,80/forecast"
            }
        }

        mock_forecast_response = Mock()
        forecast_data = {
            "properties": {
                "periods": [
                    {
                        "name": "Today",
                        "temperature": 75,
                        "temperatureUnit": "F",
                        "shortForecast": "Sunny"
                    }
                ]
            }
        }
        mock_forecast_response.json.return_value = forecast_data

        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        result = get_weather_forecast.invoke({
            "latitude": 39.7456,
            "longitude": -97.0892
        })

        assert mock_get.call_count == 2
        assert result == forecast_data

    @patch('tools.weather_api.requests.get')
    def test_handles_different_locations(self, mock_get):
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/LOX/123,456/forecast"
            }
        }

        mock_forecast_response = Mock()
        mock_forecast_response.json.return_value = {"properties": {"periods": []}}
        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        get_weather_forecast.invoke({"latitude": 34.0522, "longitude": -118.2437})

        points_call = mock_get.call_args_list[0]
        assert "34.0522,-118.2437" in points_call[0][0]

    @patch('tools.weather_api.requests.get')
    def test_handles_multiple_forecast_periods(self, mock_get):
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TOP/31,80/forecast"
            }
        }

        forecast_data = {
            "properties": {
                "periods": [
                    {"name": "Today", "temperature": 75, "temperatureUnit": "F", "shortForecast": "Sunny"},
                    {"name": "Tonight", "temperature": 55, "temperatureUnit": "F", "shortForecast": "Clear"},
                    {"name": "Tomorrow", "temperature": 78, "temperatureUnit": "F", "shortForecast": "Partly Cloudy"},
                ]
            }
        }
        mock_forecast_response = Mock()
        mock_forecast_response.json.return_value = forecast_data
        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        result = get_weather_forecast.invoke({"latitude": 39.7456, "longitude": -97.0892})

        assert result == forecast_data
        assert len(result["properties"]["periods"]) == 3

    @patch('tools.weather_api.requests.get')
    def test_handles_api_error_in_points_call(self, mock_get):
        mock_get.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            get_weather_forecast.invoke({"latitude": 39.7456, "longitude": -97.0892})

    @patch('tools.weather_api.requests.get')
    def test_handles_api_error_in_forecast_call(self, mock_get):
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TOP/31,80/forecast"
            }
        }
        mock_get.side_effect = [mock_points_response, Exception("Forecast API Error")]

        with pytest.raises(Exception, match="Forecast API Error"):
            get_weather_forecast.invoke({"latitude": 39.7456, "longitude": -97.0892})

    @patch('tools.weather_api.requests.get')
    def test_handles_malformed_json_in_forecast(self, mock_get):
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TOP/31,80/forecast"
            }
        }

        mock_forecast_response = Mock()
        mock_forecast_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        with pytest.raises(ValueError, match="Invalid JSON"):
            get_weather_forecast.invoke({"latitude": 39.7456, "longitude": -97.0892})

    @patch('tools.weather_api.requests.get')
    def test_forecast_url_construction(self, mock_get):
        expected_forecast_url = "https://api.weather.gov/gridpoints/TOP/31,80/forecast"
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {"forecast": expected_forecast_url}
        }

        mock_forecast_response = Mock()
        mock_forecast_response.json.return_value = {"properties": {"periods": []}}
        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        get_weather_forecast.invoke({"latitude": 39.7456, "longitude": -97.0892})

        assert mock_get.call_args_list[1][0][0] == expected_forecast_url

    @patch('tools.weather_api.requests.get')
    def test_with_zero_coordinates(self, mock_get):
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TEST/0,0/forecast"
            }
        }
        mock_forecast_response = Mock()
        mock_forecast_response.json.return_value = {"properties": {"periods": []}}
        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        result = get_weather_forecast.invoke({"latitude": 0.0, "longitude": 0.0})

        assert result is not None
        assert "0.0,0.0" in mock_get.call_args_list[0][0][0]

    def test_tool_has_description(self):
        assert get_weather_forecast.description is not None
        assert len(get_weather_forecast.description) > 0

    def test_tool_has_args_schema(self):
        assert get_weather_forecast.args_schema is not None

    @pytest.mark.parametrize("lat,lon", [
        (39.7456, -97.0892),
        (34.0522, -118.2437),
        (40.7128, -74.0060),
        (25.7617, -80.1918),
        (47.6062, -122.3321),
    ])
    @patch('tools.weather_api.requests.get')
    def test_various_us_locations(self, mock_get, lat, lon):
        mock_points_response = Mock()
        mock_points_response.json.return_value = {
            "properties": {
                "forecast": "https://api.weather.gov/gridpoints/TEST/1,2/forecast"
            }
        }

        mock_forecast_response = Mock()
        mock_forecast_response.json.return_value = {
            "properties": {"periods": [{"name": "Today", "temperature": 70}]}
        }
        mock_get.side_effect = [mock_points_response, mock_forecast_response]

        result = get_weather_forecast.invoke({"latitude": lat, "longitude": lon})

        assert result is not None
        assert "properties" in result
