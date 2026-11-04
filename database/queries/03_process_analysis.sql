-- =========================================
-- 03. BUSINESS PROCESS ANALYSIS
-- =========================================

SELECT
    d.department_name,
    pe.event_type,

    COUNT(*) AS total_events,

    COUNT(*) FILTER (
        WHERE pe.status = 'completed'
    ) AS completed_events,

    COUNT(*) FILTER (
        WHERE pe.status = 'in_progress'
    ) AS events_in_progress,

    COUNT(*) FILTER (
        WHERE pe.status = 'failed'
    ) AS failed_events,

    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (
                pe.completed_at - pe.started_at
            )) / 60
        ) FILTER (
            WHERE pe.status = 'completed'
        ),
        2
    ) AS average_duration_minutes,

    ROUND(
        MAX(
            EXTRACT(EPOCH FROM (
                pe.completed_at - pe.started_at
            )) / 60
        ) FILTER (
            WHERE pe.status = 'completed'
        ),
        2
    ) AS maximum_duration_minutes

FROM process_events pe

JOIN departments d
    ON pe.department_id = d.department_id

GROUP BY
    d.department_name,
    pe.event_type

ORDER BY
    average_duration_minutes DESC NULLS LAST;