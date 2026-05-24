# Edge AI UPI Risk Intelligence

Edge AI UPI Risk Intelligence is a fraud detection and transaction monitoring demo for digital payments. It combines a FastAPI backend, Streamlit dashboards, graph-based fraud analysis, explainability, and a live transaction simulator to show how a modern risk engine can score and investigate suspicious activity.

## What the project does

The platform simulates UPI-style transactions and evaluates them with behavioural risk scoring, fraud-ring detection, graph analytics, and explainable AI. It is designed to demonstrate how transaction patterns, sender/receiver relationships, and velocity signals can be used to flag risky activity.

## Main capabilities

- Live transaction scoring through the backend API
- Fraud network graph generation from stored transactions
- Fraud ring detection based on repeated or shared merchant activity
- GNN-style suspicious node detection using transaction edges
- Heatmap and alert views for risk monitoring
- Explainability output for individual transactions
- Streamlit-based dashboard pages for analysis and simulation

## Project structure

- `backend/` contains the FastAPI backend, services, graph logic, and helper modules
- `dashboard/` contains the Streamlit dashboard and page-based views
- `data/` stores local runtime data such as risk history and fallback database files
- `transactions.csv` stores transaction records used by several analysis features
- `requirements.txt` lists Python dependencies

## How to run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
python -m uvicorn backend.api:app --reload
```

Open backend docs:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

Start the dashboard:

```bash
streamlit run dashboard/dashboard.py
```

Open the dashboard:

- `http://localhost:8501`

## Working pages

- Fraud Detection
- Live Transaction Simulator
- Fraud Network Graph
- Fraud Rings
- Fraud Heatmap
- Explainability
- Fraud Alerts
- System Monitor
- GNN Fraud Detection

## Data notes

The system stores transaction history locally so the dashboard pages can render data immediately. If PostgreSQL is unavailable, the backend falls back to a local SQLite database under `data/` and continues to work.

## Example transaction input

For the simulator or `/predict`, use values like:

- User ID: `1`
- Amount: `5000`
- Device Score: `0.7`
- Location Score: `0.3`
- Velocity Score: `2`
- Sender: `user_1`
- Receiver: `merchant_5`
- Timestamp: `2026-05-24T12:00:00`

## Tech stack

- Python
- FastAPI
- Streamlit
- Pandas
- NumPy
- NetworkX
- Scikit-learn
- Matplotlib

## Author

Created as an AI-based fraud monitoring and risk intelligence demo for digital payments.
