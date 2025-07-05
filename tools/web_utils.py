import logging
from datetime import datetime
from livekit.agents import function_tool, RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun


@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        response = requests.get(
            f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}."


@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web using DuckDuckGo.
    """
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for '{query}': {results}")
        return results
    except Exception as e:
        logging.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."


@function_tool()
async def get_current_time(
    context: RunContext,  # type: ignore
) -> str:
    """
    Get the current time in HH:MM:SS format.
    """
    try:
        current_time = datetime.now().strftime("%H:%M:%S")
        logging.info(f"Current time: {current_time}")
        return f"The current time is {current_time}"
    except Exception as e:
        logging.error(f"Error getting current time: {e}")
        return "An error occurred while getting the current time."


@function_tool()
async def get_current_date(
    context: RunContext,  # type: ignore
) -> str:
    """
    Get the current date in YYYY-MM-DD format.
    """
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        logging.info(f"Current date: {current_date}")
        return f"The current date is {current_date}"
    except Exception as e:
        logging.error(f"Error getting current date: {e}")
        return "An error occurred while getting the current date."


@function_tool()
async def get_current_datetime(
    context: RunContext,  # type: ignore
) -> str:
    """
    Get the current date and time in YYYY-MM-DD HH:MM:SS format.
    """
    try:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Current datetime: {current_datetime}")
        return f"The current date and time is {current_datetime}"
    except Exception as e:
        logging.error(f"Error getting current datetime: {e}")
        return "An error occurred while getting the current date and time."