from collections import defaultdict

from backend.app.core.database import get_connection


def detect_fraud_rings():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT sender, receiver, COALESCE(risk_score, 0)
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

    merchant_map = defaultdict(lambda: {"users": [], "risk_scores": []})

    for sender, receiver, risk_score in rows:
        merchant_map[receiver]["users"].append(sender)
        merchant_map[receiver]["risk_scores"].append(float(risk_score or 0))

    suspicious_clusters = []

    for merchant, details in merchant_map.items():
        users = details["users"]
        distinct_users = sorted(set(users))
        transaction_count = len(users)
        avg_risk = sum(details["risk_scores"]) / transaction_count if transaction_count else 0

        if transaction_count >= 2 or len(distinct_users) >= 2 or avg_risk >= 300:
            suspicious_clusters.append(
                {
                    "merchant": merchant,
                    "users": distinct_users,
                    "transaction_count": transaction_count,
                    "distinct_users": len(distinct_users),
                    "avg_risk_score": round(avg_risk, 2),
                    "reason": (
                        "Repeated merchant activity"
                        if transaction_count >= 2 and len(distinct_users) <= 1
                        else "Multiple users linked to merchant"
                        if len(distinct_users) >= 2
                        else "High average risk"
                    ),
                }
            )

    suspicious_clusters.sort(
        key=lambda item: (item["distinct_users"], item["transaction_count"], item["avg_risk_score"]),
        reverse=True,
    )

    return suspicious_clusters