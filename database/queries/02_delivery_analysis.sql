-- =========================================
-- 02. DELIVERY PERFORMANCE ANALYSIS
-- =========================================

SELECT
    carrier,

    COUNT(*) AS total_shipments,

    COUNT(*) FILTER (
        WHERE delivered_at IS NOT NULL
    ) AS completed_shipments,

    COUNT(*) FILTER (
        WHERE delivery_status = 'delayed'
          AND delivered_at IS NOT NULL
    ) AS delayed_shipments,

    ROUND(
        COUNT(*) FILTER (
            WHERE delivery_status = 'delayed'
              AND delivered_at IS NOT NULL
        ) * 100.0
        / NULLIF(
            COUNT(*) FILTER (
                WHERE delivered_at IS NOT NULL
            ), 0
        ),
        2
    ) AS delay_rate_percent,

    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (delivered_at - shipped_at)) / 3600
        ) FILTER (
            WHERE delivered_at IS NOT NULL
        ),
        2
    ) AS average_delivery_hours,

    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (delivered_at - promised_delivery_at)) / 3600
        ) FILTER (
            WHERE delivered_at IS NOT NULL
        ),
        2
    ) AS average_deviation_from_promise_hours

FROM shipments

GROUP BY carrier

ORDER BY delay_rate_percent DESC;
