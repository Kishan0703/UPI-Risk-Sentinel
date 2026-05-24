import os
import importlib
import importlib.util
import sqlite3

psycopg2 = None
if importlib.util.find_spec("psycopg2") is not None:
    psycopg2 = importlib.import_module("psycopg2")


SQLITE_DB_PATH = os.path.join("data", "edge_upi_risk.sqlite3")


class SQLiteCursorAdapter:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        translated_query = query.replace("%s", "?")
        if params is None:
            return self._cursor.execute(translated_query)
        return self._cursor.execute(translated_query, params)

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    def close(self):
        return self._cursor.close()


class SQLiteConnectionAdapter:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return SQLiteCursorAdapter(self._connection.cursor())

    def commit(self):
        return self._connection.commit()

    def close(self):
        return self._connection.close()


def _init_sqlite_schema(connection):
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            user_id INTEGER,
            amount REAL,
            risk_score REAL,
            decision TEXT,
            sender TEXT,
            receiver TEXT,
            timestamp TEXT,
            time_gap REAL,
            is_night INTEGER,
            device_score REAL,
            location_score REAL,
            velocity_score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    existing_columns = {
        row[1]
        for row in cursor.execute("PRAGMA table_info(transactions)").fetchall()
    }

    required_columns = {
        "transaction_id": "TEXT",
        "sender": "TEXT",
        "receiver": "TEXT",
        "timestamp": "TEXT",
        "time_gap": "REAL",
        "is_night": "INTEGER",
        "device_score": "REAL",
        "location_score": "REAL",
        "velocity_score": "REAL",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE transactions ADD COLUMN {column_name} {column_type}"
            )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            risk_score REAL,
            risk_level TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_scores (
            user_id INTEGER PRIMARY KEY,
            trust_score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()


def _get_sqlite_connection():
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    connection = sqlite3.connect(SQLITE_DB_PATH)
    _init_sqlite_schema(connection)
    return SQLiteConnectionAdapter(connection)


def get_connection():
    if psycopg2 is None:
        return _get_sqlite_connection()

    try:
        return psycopg2.connect(
            host="localhost",
            database="edge_upi_risk",
            user="postgres",
            password="unni0666"
        )
    except Exception:
        return _get_sqlite_connection()