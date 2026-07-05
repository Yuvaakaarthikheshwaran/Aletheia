from backend.tavily_search import search_plant_tavily
from backend.parser_extractor import parse_plant_data

def get_dynamic_plant_profile(plant_name):
    results = search_plant_tavily(plant_name)

    parser_profile, confidence = parse_plant_data(plant_name, results)

    return parser_profile