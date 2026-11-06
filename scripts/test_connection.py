import os

import psycopg
from dotenv import load_dotenv

load_dotenv(override=False)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "business_analytics"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def test_connection():
    if not DB_CONFIG["password"]:
        raise SystemExit("DB_PASSWORD is not set. Add it to your .env file.")

    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM customers),
                        (SELECT COUNT(*) FROM products),
                        (SELECT COUNT(*) FROM orders),
                        (SELECT COUNT(*) FROM process_events);
                    """
                )
                customers, products, orders, events = cur.fetchone()

        print("\nSUCCESS: PostgreSQL connection established.")
        print(f"Customers: {customers}")
        print(f"Products: {products}")
        print(f"Orders: {orders}")
        print(f"Process events: {events}")
    except psycopg.Error as error:
        print("\nERROR: Database connection failed.")
        print(error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    test_connection()
