from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search_plant_tavily(plant_name):
    query = f"""
    {plant_name} plant optimal day temperature night temperature humidity
    soil moisture soil temperature light requirements growth stages
    heat stress cold stress drought stress
    """

    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=8
        )
        return response

    except Exception as e:
        print(e)
        return None