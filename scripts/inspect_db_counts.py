import psycopg2
import sqlite3

def check_postgres():
    print("=== PostgreSQL Counts ===")
    try:
        conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:5433/portfolio_rebalancing")
        cur = conn.cursor()
        tables = [
            "investor_profile", "portfolio", "instrument", "holding", "market_price",
            "target_allocation", "fee_schedule", "constraint", "constraint_instrument",
            "rebalance_proposal", "trade", "policy_documents", "policy_chunks",
            "workflow_runs", "audit_events"
        ]
        for t in tables:
            cur.execute(f'SELECT count(*) FROM "{t}"')
            print(f"  {t}: {cur.fetchone()[0]}")
    except Exception as e:
        print(f"PostgreSQL connection error: {e}")

def check_sqlite():
    print("=== SQLite Counts (data/portfolio_rebalancing.db) ===")
    try:
        conn = sqlite3.connect("data/portfolio_rebalancing.db")
        cur = conn.cursor()
        tables = [
            "investor_profile", "portfolio", "instrument", "holding", "market_price",
            "target_allocation", "fee_schedule", "constraint", "constraint_instrument",
            "rebalance_proposal", "trade", "policy_documents", "policy_chunks",
            "workflow_runs", "audit_events"
        ]
        for t in tables:
            cur.execute(f'SELECT count(*) FROM "{t}"')
            print(f"  {t}: {cur.fetchone()[0]}")
    except Exception as e:
        print(f"SQLite error: {e}")

if __name__ == "__main__":
    check_postgres()
    print()
    check_sqlite()
