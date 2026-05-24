from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from datetime import datetime
import re
import uuid

# Core services
from backend.app.core.database import get_connection

# Behaviour services
from backend.app.services.velocity_service import check_velocity
from backend.app.services.drift_service import detect_risk_drift
from backend.app.services.graph_fraud_service import detect_fraud_rings
from backend.advanced_ai.gnn_fraud_detector import gnn_risk

# AI + Alerts
from backend.app.services.alert_service import add_alert, get_alerts
from backend.app.services.shap_service import explain_transaction


app = FastAPI(title="Edge UPI Behavioural Risk Intelligence System")


# ---------------------------------------------------
# Home Route
# ---------------------------------------------------

@app.get("/")
def home():
    return RedirectResponse(url="/docs")


# ---------------------------------------------------
# Transaction Schema
# ---------------------------------------------------

class Transaction(BaseModel):
    user_id: int | None = None
    amount: float
    time_gap: float | None = None
    is_night: int | None = None
    sender: str | None = None
    receiver: str | None = None
    device_score: float | None = None
    location_score: float | None = None
    velocity_score: float | None = None
    timestamp: str | None = None


def _extract_user_id(sender: str | None, fallback: int = 0) -> int:
    if not sender:
        return fallback

    match = re.search(r"(\d+)", sender)
    if match:
        return int(match.group(1))

    return fallback


def _normalize_time_gap(tx: Transaction) -> float:
    if tx.time_gap is not None:
        return float(tx.time_gap)

    if tx.velocity_score is not None:
        return max(0.0, float(10.0 - tx.velocity_score))

    return 100.0


def _normalize_is_night(tx: Transaction) -> int:
    if tx.is_night is not None:
        return int(tx.is_night)

    if tx.timestamp:
        try:
            current_time = datetime.fromisoformat(tx.timestamp.replace("Z", "+00:00"))
            hour = current_time.hour
            return 1 if hour < 6 or hour > 22 else 0
        except Exception:
            return 0

    return 0


def _store_transaction_record(tx_id: str, tx: Transaction, risk_score: float, decision: str):
    user_id = tx.user_id if tx.user_id is not None else _extract_user_id(tx.sender, 0)
    time_gap = _normalize_time_gap(tx)
    is_night = _normalize_is_night(tx)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO transactions (
                transaction_id, user_id, amount, risk_score, decision,
                sender, receiver, timestamp, time_gap, is_night,
                device_score, location_score, velocity_score
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                tx_id,
                user_id,
                tx.amount,
                risk_score,
                decision,
                tx.sender,
                tx.receiver,
                tx.timestamp,
                time_gap,
                is_night,
                tx.device_score,
                tx.location_score,
                tx.velocity_score,
            ),
        )
    except Exception:
        cur.execute(
            """
            INSERT INTO transactions (user_id, amount, risk_score, decision)
            VALUES (%s,%s,%s,%s)
            """,
            (user_id, tx.amount, risk_score, decision),
        )

    cur.execute(
        """
        INSERT INTO risk_history (user_id, risk_score)
        VALUES (%s,%s)
        """,
        (user_id, risk_score),
    )

    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------
# Decision Engine
# ---------------------------------------------------

def decision_engine(score):

    if score < 300:
        return "APPROVE"

    elif score < 600:
        return "REVIEW"

    elif score < 800:
        return "STEP_UP_AUTH"

    else:
        return "BLOCK_TRANSACTION"


# ---------------------------------------------------
# Risk Scoring
# ---------------------------------------------------

@app.post("/score")
def score_transaction(tx: Transaction):

    resolved_user_id = tx.user_id if tx.user_id is not None else _extract_user_id(tx.sender, 0)
    resolved_time_gap = _normalize_time_gap(tx)
    resolved_is_night = _normalize_is_night(tx)

    # Base risk
    risk_score = tx.amount * 0.1

    # Velocity check
    velocity = check_velocity(resolved_user_id)

    if velocity["velocity_attack"]:
        risk_score += 200

    # Risk drift detection
    drift = detect_risk_drift(risk_score)

    # Final decision
    decision = decision_engine(risk_score)

    if tx.amount > 70000 or (tx.velocity_score or 0) > 7:
        risk = 1
    else:
        risk = 1 if risk_score >= 70 else 0

    trust_score = max(0, 1000 - risk_score)

    # Fraud alert trigger
    if risk_score > 800:
        add_alert(resolved_user_id, risk_score, decision)

    # Explainable AI
    explanation = explain_transaction(
        tx.amount,
        resolved_time_gap,
        resolved_is_night
    )

    tx_id = f"tx_{uuid.uuid4().hex[:6]}"

    _store_transaction_record(tx_id, tx, risk_score, decision)

    return {
        "risk_score": risk_score,
        "decision": decision,
        "velocity_attack": velocity["velocity_attack"],
        "risk_drift": drift,
        "trust_score": trust_score,
        "explanation": explanation,
        "transaction_id": tx_id,
    }


# ---------------------------------------------------
# Risk History
# ---------------------------------------------------

@app.get("/risk-history/{user_id}")
def risk_history(user_id: int):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT risk_score
        FROM risk_history
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    history = []

    for r in rows:
        history.append(r[0])

    return {
        "user_id": user_id,
        "history": history
    }


# ---------------------------------------------------
# Fraud Heatmap
# ---------------------------------------------------

@app.get("/fraud-heatmap")
def fraud_heatmap():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT user_id, MAX(risk_score)
        FROM risk_history
        GROUP BY user_id
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []

    for r in rows:

        data.append({
            "user_id": r[0],
            "risk_score": r[1]
        })

    return data


# ---------------------------------------------------
# Live Fraud Feed
# ---------------------------------------------------

@app.get("/fraud-feed")
def fraud_feed():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT user_id, risk_score
        FROM risk_history
        ORDER BY id DESC
        LIMIT 20
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []

    for r in rows:

        data.append({
            "user_id": r[0],
            "risk_score": r[1]
        })

    return data


# ---------------------------------------------------
# Fraud Ring Detection
# ---------------------------------------------------

@app.get("/fraud-rings")
def fraud_rings():

    rings = detect_fraud_rings()

    return {
        "rings": rings,
        "suspicious_clusters": rings
    }


# ---------------------------------------------------
# Live Fraud Alerts
# ---------------------------------------------------

@app.get("/fraud-alerts")
def fraud_alerts():

    alerts = get_alerts()

    return {
        "alerts": alerts
    }


@app.post("/predict")
def predict_transaction(tx: Transaction):
    mapped_tx = Transaction(
        user_id=tx.user_id if tx.user_id is not None else _extract_user_id(tx.sender, 1),
        amount=tx.amount,
        time_gap=_normalize_time_gap(tx),
        is_night=_normalize_is_night(tx),
        sender=tx.sender,
        receiver=tx.receiver,
        device_score=tx.device_score,
        location_score=tx.location_score,
        velocity_score=tx.velocity_score,
        timestamp=tx.timestamp,
    )
    return score_transaction(mapped_tx)


@app.get("/transactions")
def transactions():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                COALESCE(transaction_id, 'tx_' || id) AS transaction_id,
                user_id,
                amount,
                COALESCE(risk_score, 0) AS risk_score,
                CASE WHEN COALESCE(risk_score, 0) >= 70 THEN 1 ELSE 0 END AS risk,
                decision,
                sender,
                receiver,
                timestamp,
                time_gap,
                is_night,
                device_score,
                location_score,
                velocity_score
            FROM transactions
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        cur.close()
        conn.close()

    return [
        {
            "transaction_id": row[0],
            "user_id": row[1],
            "amount": row[2],
            "risk_score": row[3],
            "risk": row[4],
            "decision": row[5],
            "sender": row[6],
            "receiver": row[7],
            "timestamp": row[8],
            "time_gap": row[9],
            "is_night": row[10],
            "device_score": row[11],
            "location_score": row[12],
            "velocity_score": row[13],
        }
        for row in rows
    ]


@app.get("/fraud-graph")
def fraud_graph():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT sender, receiver
            FROM transactions
            WHERE sender IS NOT NULL AND receiver IS NOT NULL
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        cur.close()
        conn.close()

    return {
        "edges": [
            {"user": row[0], "merchant": row[1]}
            for row in rows
        ]
    }


@app.get("/heatmap")
def heatmap():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT amount, risk_score
            FROM transactions
            WHERE amount IS NOT NULL AND risk_score IS NOT NULL
            ORDER BY id DESC
            """
        )
        rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        cur.close()
        conn.close()

    if not rows:
        return {"error": "Not enough transactions"}

    return {
        "amount": [float(row[0]) for row in rows],
        "risk": [float(row[1]) for row in rows],
    }


@app.get("/explain/{tx_id}")
def explain(tx_id: str):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT amount, time_gap, is_night
            FROM transactions
            WHERE COALESCE(transaction_id, 'tx_' || id) = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (tx_id,),
        )
        row = cur.fetchone()
    except Exception:
        row = None
    finally:
        cur.close()
        conn.close()

    if row is None:
        return {"error": "Transaction Not Found"}

    amount = float(row[0] or 0)
    time_gap = float(row[1] or 0)
    is_night = int(row[2] or 0)

    return {
        "transaction_id": tx_id,
        "features": ["amount", "time_gap", "is_night"],
        "explanation": explain_transaction(amount, time_gap, is_night),
    }


@app.get("/gnn-fraud-detection")
def gnn_fraud_detection():
    edges = fraud_graph()["edges"]
    suspicious_nodes = gnn_risk(edges)
    return {"suspicious_nodes": suspicious_nodes}