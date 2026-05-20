import requests
from langchain_core.tools import tool
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from tools.constants import NWS_BASE_URL


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)
def _get_forecast_url(latitude: float, longitude: float) -> str:
    """Get the NWS forecast URL for a given latitude and longitude."""
    url = f"{NWS_BASE_URL}/points/{latitude},{longitude}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["properties"]["forecast"]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)
def _fetch_forecast(forecast_url: str) -> dict:
    """Fetch the forecast JSON from a NWS forecast URL."""
    response = requests.get(forecast_url)
    response.raise_for_status()
    return response.json()


@tool
def get_weather_forecast(latitude: float, longitude: float) -> dict:
    """Get the weather forecast for a given latitude and longitude."""
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise ValueError(f"Invalid coordinates: ({latitude}, {longitude})")

    forecast_url = _get_forecast_url(latitude, longitude)
    return _fetch_forecast(forecast_url)
