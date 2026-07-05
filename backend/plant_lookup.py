def search_plant_online(plant_name):
    plant_name = plant_name.lower()

    simulated_web_database = {
        "dragon fruit": {
            "temperature": "18-32C",
            "humidity": "50-70%",
            "soil_moisture": "35-55%",
            "light": "900-1400",
            "soil_temp": "20-30C"
        },

        "mango": {
            "temperature": "24-35C",
            "humidity": "50-80%",
            "soil_moisture": "45-65%",
            "light": "1000-1500",
            "soil_temp": "24-32C"
        },

        "aloe vera": {
            "temperature": "18-30C",
            "humidity": "20-50%",
            "soil_moisture": "15-35%",
            "light": "800-1300",
            "soil_temp": "20-30C"
        },

        "banana": {
            "temperature": "26-35C",
            "humidity": "60-90%",
            "soil_moisture": "65-85%",
            "light": "900-1400",
            "soil_temp": "24-32C"
        }
    }

    if plant_name in simulated_web_database:
        return simulated_web_database[plant_name]

    return None
