import streamlit as st
import sys
import os
import random

sys.path.append(os.path.abspath("../ai"))
from unified_engine import unified_analysis

st.set_page_config(page_title="Aletheia", layout="wide")

st.markdown("""
<style>
.main {
    background-color: #0f172a;
}
div[data-testid="metric-container"] {
    background-color: #111827;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #374151;
}
</style>
""", unsafe_allow_html=True)


def generate_data():
    current_data = {
        "air_temp": random.randint(28, 42),
        "humidity": random.randint(25, 75),
        "light": random.randint(300, 1000),
        "leaf_temp": random.randint(30, 45),
        "soil_moisture": random.randint(25, 80),
        "soil_temp": random.randint(22, 35),
        "air_temp_rate": random.randint(0, 6),
        "humidity_rate": random.randint(-20, 5),
        "leaf_temp_rate": random.randint(0, 5),
        "leaf_temp_delta": random.randint(1, 8)
    }

    temporal_data = {
        "air_temp_prev2": random.randint(28, 35),
        "air_temp_prev1": random.randint(30, 38),
        "air_temp": random.randint(30, 42),
        "humidity_prev2": random.randint(40, 70),
        "humidity_prev1": random.randint(35, 60),
        "humidity": random.randint(25, 55),
        "soil_moisture_prev2": random.randint(40, 80),
        "soil_moisture_prev1": random.randint(35, 70),
        "soil_moisture": random.randint(20, 65),
        "leaf_temp_delta_prev2": random.randint(1, 4),
        "leaf_temp_delta_prev1": random.randint(2, 6),
        "leaf_temp_delta": random.randint(3, 9)
    }

    return current_data, temporal_data


if "data" not in st.session_state:
    st.session_state.data = generate_data()

if st.button("Generate New Reading"):
    st.session_state.data = generate_data()

current_data, temporal_data = st.session_state.data
result = unified_analysis(current_data, temporal_data)

st.title("🌱 Aletheia")
st.subheader("Predictive Plant Stress Intelligence Platform")

col1, col2, col3 = st.columns(3)

sensor = result["sensor_status"]

with col1:
    st.metric("Sensor Health", f"{sensor['sensor_confidence']}%")

with col2:
    if result["status"] == "ok":
        st.metric("Current Risk", result["current_state"]["prediction"])

with col3:
    if result["status"] == "ok":
        st.metric("Future Risk", result["future_state"]["future_prediction"])

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Live Sensor Data")
    st.json(current_data)

with right:
    st.subheader("AI Insights")

    if result["status"] == "unknown_anomaly":
        st.error("Unknown anomaly detected")

    else:
        st.write("Current Analysis:")
        st.write(result["current_state"]["reasons"])

        st.write("Recommendation:")
        st.success(result["current_state"]["recommendation"])