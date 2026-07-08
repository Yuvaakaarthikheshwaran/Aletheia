
from tavily import TavilyClient
import os
from dotenv import load_dotenv
import traceback

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")
print("TAVILY KEY EXISTS:", api_key is not None)

client = TavilyClient(api_key=api_key)


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
        print("TAVILY SUCCESS")
        return response

    except Exception as e:
        print("TAVILY ERROR:", str(e))
        traceback.print_exc()
        return None

