from tavily_search import search_plant_tavily
from deepseek_extractor import extract_plant_profile

results = search_plant_tavily("tomato")
profile = extract_plant_profile("tomato", results)

print(profile)
