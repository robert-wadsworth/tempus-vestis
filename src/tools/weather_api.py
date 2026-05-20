import requests
from langchain_core.tools import tool

from tools.constants import NWS_BASE_URL


def _get_forecast_url(latitude: float, longitude: float) -> str:
    """Get the NWS forecast URL for a given latitude and longitude."""
    url = f"{NWS_BASE_URL}/points/{latitude},{longitude}"
    data = requests.get(url).json()
    return data["properties"]["forecast"]


@tool
def get_weather_forecast(latitude: float, longitude: float) -> dict:
    """Get the weather forecast for a given latitude and longitude."""
    forecast_url = _get_forecast_url(latitude, longitude)
    return requests.get(forecast_url).json()
