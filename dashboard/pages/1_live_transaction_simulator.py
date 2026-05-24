import streamlit as st
import requests
from datetime import datetime

API = "http://127.0.0.1:8000"


def detect_backend_endpoint(base_url):
    """Pick the backend route exposed by the running app."""
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=3)
        response.raise_for_status()
        paths = response.json().get("paths", {})
    except requests.exceptions.RequestException:
        paths = {}

    if "/score" in paths:
        return "/score", "api"
    if "/predict" in paths:
        return "/predict", "main"

    return None, None

st.title("Live Transaction Simulator")

user_id = st.number_input("User ID", value=1, min_value=1)

amount = st.number_input("Amount", value=5000)

device_score = st.slider("Device Score", 0.0, 1.0, 0.7)

location_score = st.slider("Location Score", 0.0, 1.0, 0.3)

velocity_score = st.slider("Velocity Score", 0.0, 10.0, 2.0)

sender = st.text_input("Sender", "user_1")

receiver = st.text_input("Receiver", "merchant_5")

if st.button("Simulate Transaction"):

    # Map simulator fields to the backend `Transaction` schema:
    # Transaction requires: user_id (int), amount (float), time_gap (float), is_night (int)
    hour = datetime.now().hour
    is_night = 1 if (hour < 6 or hour >= 22) else 0

    # Use velocity_score as a proxy for time_gap (lower velocity -> larger time gap)
    time_gap = max(0.0, float(10.0 - velocity_score))

    data = {
        "user_id": int(user_id),
        "amount": float(amount),
        "time_gap": float(time_gap),
        "is_night": int(is_night),
        "sender": sender,
        "receiver": receiver,
        "device_score": float(device_score),
        "location_score": float(location_score),
        "velocity_score": float(velocity_score),
        "timestamp": str(datetime.now())
    }

    predict_data = {
        "amount": float(amount),
        "device_score": float(device_score),
        "location_score": float(location_score),
        "velocity_score": float(velocity_score),
        "sender": sender,
        "receiver": receiver,
        "timestamp": str(datetime.now())
    }

    endpoint, backend_type = detect_backend_endpoint(API)

    try:
        if endpoint == "/score":
            res = requests.post(API + endpoint, json=data, timeout=5)
        elif endpoint == "/predict":
            res = requests.post(API + endpoint, json=predict_data, timeout=5)
        else:
            st.error("No compatible backend endpoint found. Start backend.api:app or backend.main:app.")
            st.stop()

        if res.status_code == 200:
            result = res.json()
            st.caption(f"Connected to {backend_type} backend at {endpoint}")
            st.json(result)
        else:
            st.error(f"Backend returned status {res.status_code}: {res.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to contact backend: {e}")