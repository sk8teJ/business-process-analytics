-- =========================================
-- 01. KEY BUSINESS METRICS
-- =========================================

WITH payment_metrics AS (
    SELECT
        COUNT(*) FILTER (
            WHERE status = 'successful'
        ) AS successful_payments,

        COALESCE(
            SUM(amount) FILTER (
                WHERE status = 'successful'
            ), 0
        ) AS gross_revenue

    FROM payments
),

return_metrics AS (
    SELECT
        COUNT(*) AS return_count,

        COALESCE(
            SUM(refund_amount) FILTER (
                WHERE status = 'completed'
            ), 0
        ) AS completed_refunds

    FROM returns
),

order_metrics AS (
    SELECT
        COUNT(*) AS total_orders,

        COUNT(*) FILTER (
            WHERE status = 'delivered'
        ) AS delivered_orders,

        COUNT(*) FILTER (
            WHERE status = 'cancelled'
        ) AS cancelled_orders

    FROM orders
)

SELECT
    o.total_orders,
    o.delivered_orders,
    o.cancelled_orders,
    p.successful_payments,
    r.return_count,
    p.gross_revenue,
    r.completed_refunds,

    p.gross_revenue - r.completed_refunds AS net_revenue,

    ROUND(
        p.gross_revenue / NULLIF(p.successful_payments, 0),
        2
    ) AS average_successful_payment,

    ROUND(
        o.cancelled_orders * 100.0 / NULLIF(o.total_orders, 0),
        2
    ) AS cancellation_rate_percent

FROM order_metrics o
CROSS JOIN payment_metrics p
CROSS JOIN return_metrics r;