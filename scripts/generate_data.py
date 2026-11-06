import argparse
import os
import random
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv(override=False)
random.seed(42)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "business_analytics"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

START_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)

CUSTOMERS_COUNT = 500
ORDERS_COUNT = 2000

CITIES = [
    "Moscow", "Saint Petersburg", "Nizhny Novgorod",
    "Kazan", "Samara", "Yekaterinburg", "Novosibirsk",
    "Krasnodar", "Rostov-on-Don", "Perm",
]

FIRST_NAMES = [
    "Alex", "Daniel", "Michael", "Ivan", "Alexander",
    "Dmitry", "Anna", "Maria", "Elena", "Olga",
]

LAST_NAMES = [
    "Smith", "Brown", "Ivanov", "Petrov", "Sidorov",
    "Johnson", "Williams", "Taylor", "Wilson", "Anderson",
]

PRODUCTS = [
    ("Electronics", "Wireless headphones", 4500),
    ("Electronics", "Bluetooth speaker", 3200),
    ("Electronics", "Smart watch", 6500),
    ("Electronics", "Power bank", 1800),
    ("Electronics", "USB cable", 500),
    ("Home", "Desk lamp", 2100),
    ("Home", "Coffee maker", 7200),
    ("Home", "Electric kettle", 2800),
    ("Home", "Storage organizer", 900),
    ("Home", "Table clock", 1500),
    ("Clothing", "T-shirt", 1200),
    ("Clothing", "Hoodie", 3500),
    ("Clothing", "Jeans", 4200),
    ("Clothing", "Jacket", 7800),
    ("Clothing", "Sneakers", 5900),
    ("Sports", "Yoga mat", 1600),
    ("Sports", "Dumbbells", 2400),
    ("Sports", "Fitness band", 1100),
    ("Sports", "Water bottle", 700),
    ("Sports", "Sports bag", 2600),
]

DEPARTMENTS = [
    "Sales",
    "Warehouse",
    "Payment",
    "Delivery",
    "Customer Support",
]

# Условная продолжительность этапов бизнес-процесса.
# Значения используются для учебного моделирования.
DURATION_RANGES = {
    "Sales": (2, 20),
    "Payment": (1, 30),
    "Warehouse": (30, 360),
    "Delivery": (1440, 7200),
}


def random_date():
    seconds = int((END_DATE - START_DATE).total_seconds())
    return START_DATE + timedelta(seconds=random.randint(0, seconds - 1))


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_data(confirm=False):
    if not confirm:
        print("\nWARNING: this script truncates all demo tables and replaces their contents.")
        answer = input("Type REGENERATE to continue: ").strip()
        if answer != "REGENERATE":
            print("Cancelled. No data was changed.")
            return

    if not DB_CONFIG["password"]:
        raise SystemExit("DB_PASSWORD is not set. Add it to your .env file.")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            print("Clearing old test data...")

            cur.execute("""
                TRUNCATE TABLE
                    process_events,
                    returns,
                    shipments,
                    payments,
                    order_items,
                    orders,
                    departments,
                    products,
                    customers
                RESTART IDENTITY CASCADE;
            """)

            print("Creating departments...")

            department_ids = {}

            for department in DEPARTMENTS:
                cur.execute(
                    """
                    INSERT INTO departments (department_name)
                    VALUES (%s)
                    RETURNING department_id;
                    """,
                    (department,),
                )
                department_ids[department] = cur.fetchone()[0]

            print("Creating customers...")

            customer_ids = []

            for number in range(CUSTOMERS_COUNT):
                name = random_name()
                email = f"customer{number + 1}@example.com"
                city = random.choice(CITIES)

                cur.execute(
                    """
                    INSERT INTO customers (full_name, email, city)
                    VALUES (%s, %s, %s)
                    RETURNING customer_id;
                    """,
                    (name, email, city),
                )

                customer_ids.append(cur.fetchone()[0])

            print("Creating products...")

            product_ids = []

            for number, (category, name, price) in enumerate(PRODUCTS, start=1):
                cur.execute(
                    """
                    INSERT INTO products
                        (sku, product_name, category, unit_price)
                    VALUES (%s, %s, %s, %s)
                    RETURNING product_id;
                    """,
                    (f"SKU-{number:03d}", name, category, price),
                )

                product_ids.append(cur.fetchone()[0])

            print("Creating orders and related records...")

            for order_number in range(ORDERS_COUNT):
                customer_id = random.choice(customer_ids)
                order_date = random_date()
                city = random.choice(CITIES)

                channel = random.choices(
                    ["website", "mobile_app", "marketplace"],
                    weights=[55, 30, 15],
                )[0]

                order_status = random.choices(
                    ["delivered", "shipped", "processing", "new", "cancelled"],
                    weights=[70, 10, 8, 6, 6],
                )[0]

                selected_products = random.sample(
                    product_ids,
                    random.randint(1, 4),
                )

                items = []
                total_amount = 0

                for product_id in selected_products:
                    quantity = random.randint(1, 3)

                    cur.execute(
                        "SELECT unit_price FROM products WHERE product_id = %s",
                        (product_id,),
                    )
                    unit_price = cur.fetchone()[0]

                    items.append((product_id, quantity, unit_price))
                    total_amount += quantity * unit_price

                cur.execute(
                    """
                    INSERT INTO orders
                        (customer_id, order_date, delivery_city,
                         status, channel, total_amount)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING order_id;
                    """,
                    (
                        customer_id,
                        order_date,
                        city,
                        order_status,
                        channel,
                        total_amount,
                    ),
                )

                order_id = cur.fetchone()[0]

                order_item_ids = []

                for product_id, quantity, unit_price in items:
                    cur.execute(
                        """
                        INSERT INTO order_items
                            (order_id, product_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        RETURNING order_item_id;
                        """,
                        (order_id, product_id, quantity, unit_price),
                    )

                    order_item_ids.append(
                        (cur.fetchone()[0], quantity, unit_price)
                    )

                payment_status = random.choices(
                    ["successful", "pending", "failed"],
                    weights=[88, 7, 5],
                )[0]

                if order_status == "cancelled":
                    payment_status = "failed"

                payment_date = (
                    order_date + timedelta(minutes=random.randint(1, 60))
                    if payment_status != "pending"
                    else None
                )

                cur.execute(
                    """
                    INSERT INTO payments
                        (order_id, payment_date, amount,
                         payment_method, status)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (
                        order_id,
                        payment_date,
                        total_amount,
                        random.choice(["card", "cash", "sbp"]),
                        payment_status,
                    ),
                )

                if order_status != "cancelled":
                    shipped_at = order_date + timedelta(
                        hours=random.randint(2, 48)
                    )

                    promised_at = shipped_at + timedelta(
                        days=random.randint(2, 5)
                    )

                    if order_status == "delivered":
                        is_delayed = random.random() < 0.18
                        delivered_at = promised_at + timedelta(
                            hours=random.randint(2, 48)
                            if is_delayed
                            else -random.randint(1, 36)
                        )
                        delivery_status = (
                            "delayed" if is_delayed else "delivered"
                        )
                    elif order_status == "shipped":
                        delivered_at = None
                        delivery_status = random.choice(
                            ["in_transit", "delayed"]
                        )
                    else:
                        delivered_at = None
                        delivery_status = "waiting"

                    cur.execute(
                        """
                        INSERT INTO shipments
                            (order_id, carrier, shipped_at,
                             promised_delivery_at, delivered_at,
                             delivery_status, shipping_cost)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            order_id,
                            random.choice(
                                ["CDEK", "Russian Post", "Boxberry", "DHL"]
                            ),
                            shipped_at,
                            promised_at,
                            delivered_at,
                            delivery_status,
                            random.randint(150, 900),
                        ),
                    )

                current_time = order_date

                stages = [
                    ("Sales", "Order registration"),
                    ("Payment", "Payment processing"),
                    ("Warehouse", "Order picking"),
                ]

                if order_status != "cancelled":
                    stages.append(("Delivery", "Order delivery"))

                for department, event_type in stages:
                    min_minutes, max_minutes = DURATION_RANGES[department]

                    duration = timedelta(
                        minutes=random.randint(min_minutes, max_minutes)
                    )

                    started_at = current_time
                    completed_at = started_at + duration

                    if (
                        order_status in ("new", "processing")
                        and department == "Warehouse"
                    ):
                        event_status = "in_progress"
                        completed_at = None
                    elif (
                        order_status == "cancelled"
                        and department == "Payment"
                    ):
                        event_status = "failed"
                    else:
                        event_status = "completed"

                    cur.execute(
                        """
                        INSERT INTO process_events
                            (order_id, department_id, event_type,
                             started_at, completed_at, status, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            order_id,
                            department_ids[department],
                            event_type,
                            started_at,
                            completed_at,
                            event_status,
                            None,
                        ),
                    )

                    current_time = completed_at or started_at

                if (
                    order_status == "delivered"
                    and random.random() < 0.08
                ):
                    item_id, quantity, unit_price = random.choice(order_item_ids)
                    returned_quantity = random.randint(1, quantity)

                    cur.execute(
                        """
                        INSERT INTO returns
                            (order_item_id, return_date, quantity,
                             reason, refund_amount, status)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (
                            item_id,
                            order_date + timedelta(days=random.randint(5, 30)),
                            returned_quantity,
                            random.choice(
                                [
                                    "Damaged item",
                                    "Wrong size",
                                    "Not as described",
                                    "Changed mind",
                                    "Defective product",
                                ]
                            ),
                            returned_quantity * unit_price,
                            random.choice(
                                ["approved", "completed", "rejected"]
                            ),
                        ),
                    )

                if (order_number + 1) % 500 == 0:
                    print(f"Created {order_number + 1} orders...")

    print("\nSUCCESS: test data generated.")
    print(f"Customers: {CUSTOMERS_COUNT}")
    print(f"Products: {len(PRODUCTS)}")
    print(f"Orders: {ORDERS_COUNT}")
    print("Period: 2025-01-01 — 2025-12-31")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Regenerate the synthetic online-store dataset."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the confirmation prompt (the database tables will still be truncated)",
    )
    args = parser.parse_args()
    generate_data(confirm=args.yes)