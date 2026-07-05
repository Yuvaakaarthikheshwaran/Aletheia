from rapidfuzz import process

KNOWN_PLANTS = [
    "tomato",
    "potato",
    "banana",
    "mango",
    "rice",
    "cactus",
    "aloe vera",
    "dragon fruit"
]


def search_plants(query):
    results = process.extract(query, KNOWN_PLANTS, limit=5)

    filtered = []
    for name, score, _ in results:
        if score >= 50:
            filtered.append({
                "plant": name,
                "score": score
            })

    return filtered
