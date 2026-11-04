import psycopg
from getpass import getpass

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "business_analytics",
    "user": "postgres",
}


def test_connection():
    password = getpass("Enter PostgreSQL password: ")

    try:
        with psycopg.connect(
            **DB_CONFIG,
            password=password
        ) as conn:

            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        (SELECT COUNT(*) FROM customers),
                        (SELECT COUNT(*) FROM products),
                        (SELECT COUNT(*) FROM orders),
                        (SELECT COUNT(*) FROM process_events);
                """)

                customers, products, orders, events = cur.fetchone()

        print("\nSUCCESS: PostgreSQL connection established.")
        print(f"Customers: {customers}")
        print(f"Products: {products}")
        print(f"Orders: {orders}")
        print(f"Process events: {events}")

    except Exception as error:
        print("\nERROR: Database connection failed.")
        print(error)


if __name__ == "__main__":
    test_connection()