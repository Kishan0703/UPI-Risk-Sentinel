import streamlit as st
import requests

API = "http://127.0.0.1:8000"

st.title("Detected Fraud Rings")

data = requests.get(f"{API}/fraud-rings").json()

rings = data["rings"]

if len(rings) == 0:

    st.success("No fraud rings detected")

else:

    for r in rings:
        merchant = r.get("merchant", "unknown") if isinstance(r, dict) else r[1]
        users = r.get("users", []) if isinstance(r, dict) else r[0]
        reason = r.get("reason", "Suspicious merchant activity") if isinstance(r, dict) else "Suspicious merchant activity"

        st.warning(
            f"Merchant: {merchant} | Users: {', '.join(users) if isinstance(users, list) else users} | {reason}"
        )