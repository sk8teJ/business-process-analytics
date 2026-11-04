-- =========================================
-- BUSINESS PROCESS ANALYTICS
-- Database schema: online store
-- PostgreSQL 17
-- =========================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    city VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS departments (
    department_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    order_date TIMESTAMPTZ NOT NULL,
    delivery_city VARCHAR(100),
    status VARCHAR(30) NOT NULL CHECK (
        status IN (
            'new',
            'processing',
            'shipped',
            'delivered',
            'cancelled'
        )
    ),
    channel VARCHAR(30) NOT NULL CHECK (
        channel IN ('website', 'mobile_app', 'marketplace')
    ),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    UNIQUE (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    payment_date TIMESTAMPTZ,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    payment_method VARCHAR(30) NOT NULL CHECK (
        payment_method IN ('card', 'cash', 'sbp')
    ),
    status VARCHAR(30) NOT NULL CHECK (
        status IN ('pending', 'successful', 'failed', 'refunded')
    )
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    carrier VARCHAR(100),
    shipped_at TIMESTAMPTZ,
    promised_delivery_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    delivery_status VARCHAR(30) NOT NULL CHECK (
        delivery_status IN (
            'waiting',
            'in_transit',
            'delivered',
            'delayed',
            'lost'
        )
    ),
    shipping_cost NUMERIC(10, 2) NOT NULL DEFAULT 0
        CHECK (shipping_cost >= 0)
);

CREATE TABLE IF NOT EXISTS returns (
    return_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_item_id BIGINT NOT NULL REFERENCES order_items(order_item_id),
    return_date TIMESTAMPTZ NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    reason VARCHAR(200) NOT NULL,
    refund_amount NUMERIC(12, 2) NOT NULL CHECK (refund_amount >= 0),
    status VARCHAR(30) NOT NULL CHECK (
        status IN ('requested', 'approved', 'rejected', 'completed')
    )
);

CREATE TABLE IF NOT EXISTS process_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    department_id BIGINT NOT NULL REFERENCES departments(department_id),
    event_type VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL CHECK (
        status IN ('in_progress', 'completed', 'failed')
    ),
    notes TEXT,
    CHECK (
        completed_at IS NULL OR completed_at >= started_at
    )
);

-- =========================================
-- INDEXES FOR ANALYTICAL QUERIES
-- =========================================

CREATE INDEX IF NOT EXISTS idx_orders_customer
    ON orders(customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_date
    ON orders(order_date);

CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders(status);

CREATE INDEX IF NOT EXISTS idx_order_items_order
    ON order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_payments_order
    ON payments(order_id);

CREATE INDEX IF NOT EXISTS idx_shipments_order
    ON shipments(order_id);

CREATE INDEX IF NOT EXISTS idx_returns_order_item
    ON returns(order_item_id);

CREATE INDEX IF NOT EXISTS idx_process_events_order
    ON process_events(order_id);

CREATE INDEX IF NOT EXISTS idx_process_events_department
    ON process_events(department_id);