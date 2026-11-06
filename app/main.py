
import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st
from dotenv import load_dotenv

from app.metrics import calculate_automation_roi, calculate_return_rate


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv(override=False)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "business_analytics"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

st.set_page_config(
    page_title="Business Process Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# DESIGN
# =========================================================

st.markdown(
    """
    <style>
        .stApp {
            background-color: #0e1117;
        }

        [data-testid="stSidebar"] {
            background-color: #151922;
        }

        [data-testid="stMetric"] {
            background-color: #1a202b;
            border: 1px solid #293241;
            padding: 18px;
            border-radius: 12px;
        }

        [data-testid="stMetricLabel"] {
            color: #aab4c3;
        }

        [data-testid="stMetricValue"] {
            color: #ffffff;
        }

        h1, h2, h3 {
            color: #ffffff;
        }

        .subtitle {
            color: #929eae;
            font-size: 14px;
            margin-top: -12px;
            margin-bottom: 24px;
        }

        .section-label {
            color: #8c9aad;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATABASE
# =========================================================

def get_data(sql, params=()):
    if not DB_CONFIG["password"]:
        raise ValueError(
            "Database password not found. "
            "Check DB_PASSWORD in the .env file."
        )

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            columns = [column.name for column in cur.description]

    return pd.DataFrame(rows, columns=columns)


# =========================================================
# HEADER
# =========================================================

st.title("Business Process Analytics")

st.markdown(
    '<div class="subtitle">'
    'Operational analytics platform · Online store · PostgreSQL'
    '</div>',
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR AND FILTERS
# =========================================================

st.sidebar.title("Analytics")
st.sidebar.markdown("### Reporting period")

start_date = st.sidebar.date_input(
    "Start date",
    value=date(2025, 1, 1),
    min_value=date(2025, 1, 1),
    max_value=date(2025, 12, 31),
)

end_date = st.sidebar.date_input(
    "End date",
    value=date(2025, 12, 31),
    min_value=date(2025, 1, 1),
    max_value=date(2025, 12, 31),
)

if start_date > end_date:
    st.error("The start date cannot be later than the end date.")
    st.stop()

date_params = (
    start_date,
    end_date + timedelta(days=1),
)

st.sidebar.divider()
st.sidebar.caption("Data source: PostgreSQL")
st.sidebar.caption("Dataset: synthetic online store data")
st.sidebar.caption("Period: 2025")


# =========================================================
# LOAD DATA
# =========================================================

try:
    with st.spinner("Loading analytics from PostgreSQL..."):

        # -------------------------------------------------
        # BUSINESS METRICS
        # -------------------------------------------------

        kpi = get_data(
            """
            SELECT
                COUNT(DISTINCT o.order_id) AS total_orders,

                COUNT(DISTINCT o.order_id)
                    FILTER (WHERE o.status = 'delivered')
                    AS delivered_orders,

                COUNT(DISTINCT o.order_id)
                    FILTER (WHERE o.status = 'cancelled')
                    AS cancelled_orders,

                COUNT(DISTINCT p.payment_id)
                    FILTER (WHERE p.status = 'successful')
                    AS successful_payments,

                COALESCE(
                    SUM(p.amount)
                    FILTER (WHERE p.status = 'successful'),
                    0
                ) AS gross_revenue,

                (
                    SELECT COUNT(*)
                    FROM returns r
                    JOIN order_items oi
                        ON r.order_item_id = oi.order_item_id
                    JOIN orders ro
                        ON oi.order_id = ro.order_id
                    WHERE ro.order_date >= %s
                      AND ro.order_date < %s
                ) AS return_count,

                (
                    SELECT COUNT(DISTINCT oi.order_id)
                    FROM returns r
                    JOIN order_items oi
                        ON r.order_item_id = oi.order_item_id
                    JOIN orders ro
                        ON oi.order_id = ro.order_id
                    WHERE ro.order_date >= %s
                      AND ro.order_date < %s
                ) AS returned_orders_count,

                (
                    SELECT COALESCE(SUM(r.refund_amount), 0)
                    FROM returns r
                    JOIN order_items oi
                        ON r.order_item_id = oi.order_item_id
                    JOIN orders ro
                        ON oi.order_id = ro.order_id
                    WHERE ro.order_date >= %s
                      AND ro.order_date < %s
                      AND r.status = 'completed'
                ) AS completed_refunds

            FROM orders o

            LEFT JOIN payments p
                ON o.order_id = p.order_id

            WHERE o.order_date >= %s
              AND o.order_date < %s;
            """,
            (
                *date_params,
                *date_params,
                *date_params,
                *date_params,
            ),
        )

        # -------------------------------------------------
        # MONTHLY REVENUE
        # -------------------------------------------------

        monthly_revenue = get_data(
            """
            SELECT
                DATE_TRUNC('month', p.payment_date)::date AS month,
                SUM(p.amount) AS revenue

            FROM payments p
            JOIN orders o
                ON p.order_id = o.order_id

            WHERE o.order_date >= %s
              AND o.order_date < %s
              AND p.status = 'successful'

            GROUP BY DATE_TRUNC('month', p.payment_date)

            ORDER BY month;
            """,
            date_params,
        )

        # -------------------------------------------------
        # ORDER STATUS
        # -------------------------------------------------

        order_status = get_data(
            """
            SELECT
                status,
                COUNT(*) AS orders_count

            FROM orders

            WHERE order_date >= %s
              AND order_date < %s

            GROUP BY status
            ORDER BY orders_count DESC;
            """,
            date_params,
        )

        # -------------------------------------------------
        # PROCESS ANALYSIS
        # -------------------------------------------------

        process_data = get_data(
            """
            SELECT
                d.department_name,

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
                ) AS average_duration_minutes

            FROM process_events pe

            JOIN departments d
                ON pe.department_id = d.department_id

            JOIN orders o
                ON pe.order_id = o.order_id

            WHERE o.order_date >= %s
              AND o.order_date < %s

            GROUP BY d.department_name

            ORDER BY average_duration_minutes DESC NULLS LAST;
            """,
            date_params,
        )

        # -------------------------------------------------
        # DELIVERY ANALYSIS
        # -------------------------------------------------

        delivery_data = get_data(
            """
            SELECT
                s.carrier,

                COUNT(*) AS total_shipments,

                COUNT(*) FILTER (
                    WHERE s.delivered_at IS NOT NULL
                ) AS completed_shipments,

                COUNT(*) FILTER (
                    WHERE s.delivery_status = 'delayed'
                      AND s.delivered_at IS NOT NULL
                ) AS delayed_shipments,

                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE s.delivery_status = 'delayed'
                          AND s.delivered_at IS NOT NULL
                    )
                    / NULLIF(
                        COUNT(*) FILTER (
                            WHERE s.delivered_at IS NOT NULL
                        ),
                        0
                    ),
                    2
                ) AS delay_rate_percent

            FROM shipments s

            JOIN orders o
                ON s.order_id = o.order_id

            WHERE o.order_date >= %s
              AND o.order_date < %s

            GROUP BY s.carrier

            ORDER BY delay_rate_percent DESC;
            """,
            date_params,
        )

except Exception as error:
    st.error("Could not load data from PostgreSQL.")
    st.exception(error)
    st.stop()


# =========================================================
# KPI CALCULATIONS
# =========================================================

metrics = kpi.iloc[0]

total_orders = int(metrics["total_orders"])
delivered_orders = int(metrics["delivered_orders"])
cancelled_orders = int(metrics["cancelled_orders"])
successful_payments = int(metrics["successful_payments"])

gross_revenue = float(metrics["gross_revenue"])
completed_refunds = float(metrics["completed_refunds"])
net_revenue = gross_revenue - completed_refunds

return_count = int(metrics["return_count"])
returned_orders_count = int(metrics["returned_orders_count"])

cancellation_rate = (
    cancelled_orders / total_orders * 100
    if total_orders
    else 0
)

return_rate = calculate_return_rate(returned_orders_count, total_orders)


# =========================================================
# OVERVIEW
# =========================================================

st.markdown(
    '<div class="section-label">Overview</div>',
    unsafe_allow_html=True,
)

st.header("Store performance")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total orders",
    f"{total_orders:,}".replace(",", " "),
)

col2.metric(
    "Net revenue",
    f"{net_revenue:,.0f}".replace(",", " "),
)

col3.metric(
    "Delivered orders",
    f"{delivered_orders:,}".replace(",", " "),
)

col4.metric(
    "Cancellation rate",
    f"{cancellation_rate:.2f}%",
)

st.write("")

col5, col6, col7, col8 = st.columns(4)

col5.metric(
    "Successful payments",
    f"{successful_payments:,}".replace(",", " "),
)

col6.metric(
    "Gross revenue",
    f"{gross_revenue:,.0f}".replace(",", " "),
)

col7.metric(
    "Completed refunds",
    f"{completed_refunds:,.0f}".replace(",", " "),
)

col8.metric(
    "Return requests",
    f"{return_count:,}".replace(",", " "),
)


# =========================================================
# SALES ANALYTICS
# =========================================================

st.divider()
st.header("Sales analytics")

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.subheader("Monthly revenue")

    if not monthly_revenue.empty:
        fig = px.line(
            monthly_revenue,
            x="month",
            y="revenue",
            markers=True,
            labels={
                "month": "Month",
                "revenue": "Revenue",
            },
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No revenue data for the selected period.")

with chart_col2:
    st.subheader("Order status")

    if not order_status.empty:
        fig = px.pie(
            order_status,
            names="status",
            values="orders_count",
            hole=0.58,
            labels={
                "status": "Order status",
                "orders_count": "Orders",
            },
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No order data for the selected period.")


# =========================================================
# BUSINESS PROCESS ANALYSIS
# =========================================================

st.divider()

st.markdown(
    '<div class="section-label">Operations</div>',
    unsafe_allow_html=True,
)

st.header("Business process analysis")

if not process_data.empty:
    fig = px.bar(
        process_data.sort_values("average_duration_minutes"),
        x="average_duration_minutes",
        y="department_name",
        orientation="h",
        text="average_duration_minutes",
        labels={
            "average_duration_minutes": "Average duration (minutes)",
            "department_name": "Department",
        },
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Process details")

    st.dataframe(
        process_data,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No process events for the selected period.")


# =========================================================
# DELIVERY ANALYSIS
# =========================================================

st.divider()
st.header("Delivery performance")

if not delivery_data.empty:
    fig = px.bar(
        delivery_data,
        x="carrier",
        y="delay_rate_percent",
        text="delay_rate_percent",
        labels={
            "carrier": "Carrier",
            "delay_rate_percent": "Delay rate (%)",
        },
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Carrier details")

    st.dataframe(
        delivery_data,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No delivery data for the selected period.")


# =========================================================
# AUTOMATED BUSINESS INSIGHTS
# =========================================================

st.divider()

st.markdown(
    '<div class="section-label">Business intelligence</div>',
    unsafe_allow_html=True,
)

st.header("Automated business insights")

st.caption(
    "Выводы формируются автоматически на основе показателей "
    "за выбранный период. Данные учебные и синтетические."
)


# ---------------------------------------------------------
# OPERATIONAL FINDINGS
# ---------------------------------------------------------

st.subheader("Operational findings")

insight_col1, insight_col2 = st.columns(2)

with insight_col1:
    st.markdown("#### Longest process stage")

    if not process_data.empty:
        valid_processes = process_data.dropna(
            subset=["average_duration_minutes"]
        )

        if not valid_processes.empty:
            slowest = valid_processes.loc[
                valid_processes["average_duration_minutes"].idxmax()
            ]

            st.warning(
                f"Наибольшая средняя продолжительность у этапа "
                f"**{slowest['department_name']}**. "
                f"Средняя продолжительность: "
                f"**{slowest['average_duration_minutes']:.1f} мин.**"
            )

            st.caption(
                "Большая длительность сама по себе не доказывает наличие узкого места. "
                "Для такого вывода также нужны данные о загрузке и пропускной способности."
            )

            unfinished = int(
                process_data["events_in_progress"].sum()
            )

            failed = int(
                process_data["failed_events"].sum()
            )

            st.write(f"Событий в работе: **{unfinished}**")
            st.write(f"Неуспешных событий: **{failed}**")

            if unfinished > 0:
                st.info(
                    "Есть незавершённые операции. "
                    "Стоит проверить причины накопления очереди."
                )

            if failed > 0:
                st.warning(
                    "Обнаружены неуспешные операции. "
                    "Рекомендуется проверить причины сбоев."
                )
        else:
            st.info(
                "Недостаточно данных о продолжительности процессов."
            )
    else:
        st.info("Нет данных о бизнес-процессах.")

with insight_col2:
    st.markdown("#### Delivery performance")

    if not delivery_data.empty:
        valid_delivery = delivery_data.dropna(
            subset=["delay_rate_percent"]
        )

        if not valid_delivery.empty:
            worst_carrier = valid_delivery.loc[
                valid_delivery["delay_rate_percent"].idxmax()
            ]

            best_carrier = valid_delivery.loc[
                valid_delivery["delay_rate_percent"].idxmin()
            ]

            st.warning(
                f"Наибольшая доля задержек у перевозчика "
                f"**{worst_carrier['carrier']}**: "
                f"**{worst_carrier['delay_rate_percent']:.2f}%**."
            )

            st.success(
                f"Наименьшая доля задержек у перевозчика "
                f"**{best_carrier['carrier']}**: "
                f"**{best_carrier['delay_rate_percent']:.2f}%**."            )

            st.caption(
                "Сравнение отражает только синтетический набор данных "
                "этого проекта и не характеризует реальных перевозчиков."
            )
        else:
            st.info("Недостаточно данных о задержках доставки.")
    else:
        st.info("Нет данных о доставке.")


# ---------------------------------------------------------
# SALES AND CUSTOMER EXPERIENCE
# ---------------------------------------------------------

st.subheader("Sales and customer experience")

sales_col1, sales_col2 = st.columns(2)

with sales_col1:
    st.metric(
        "Cancellation rate",
        f"{cancellation_rate:.2f}%",
    )

    if cancellation_rate > 10:
        st.warning(
            "Доля отмен превышает 10%. "
            "Стоит изучить причины отмен и этапы оформления заказов."
        )
    else:
        st.info(
            "Доля отмен не превышает 10% в выбранном периоде."
        )

with sales_col2:
    st.metric(
        "Return rate",
        f"{return_rate:.2f}%",
    )

    if return_rate > 10:
        st.warning(
            "Количество возвратов относительно заказов превышает 10%. "
            "Рекомендуется проверить причины возвратов и категории товаров."
        )
    else:
        st.info(
            "Количество возвратов относительно заказов "
            "не превышает 10% в выбранном периоде."
        )


# =========================================================
# AUTOMATION ROI CALCULATOR
# =========================================================

st.divider()

st.markdown(
    '<div class="section-label">Automation economics</div>',
    unsafe_allow_html=True,
)

st.header("Automation opportunity calculator")

st.write(
    "Калькулятор оценивает условный экономический эффект "
    "от сокращения трудозатрат на выбранном этапе процесса."
)

if not process_data.empty:
    available_departments = (
        process_data["department_name"]
        .dropna()
        .tolist()
    )

    if available_departments:
        selected_department = st.selectbox(
            "Select business process",
            available_departments,
        )

        selected_process = process_data[
            process_data["department_name"] == selected_department
        ].iloc[0]

        completed_events_count = int(
            selected_process["completed_events"]
        )

        duration_value = selected_process["average_duration_minutes"]
        average_duration = (
            float(duration_value) if pd.notna(duration_value) else 0.0
        )

        st.write(
            f"Количество завершённых событий за выбранный период: "
            f"**{completed_events_count:,}**".replace(",", " ")
        )

        st.write(
            f"Средняя продолжительность события: "
            f"**{average_duration:.2f} мин.**"
        )

        st.caption(
            "Следующие параметры — сценарные предположения. "
            "Изменяй их, чтобы оценивать разные варианты автоматизации."
        )

        roi_col1, roi_col2, roi_col3 = st.columns(3)

        with roi_col1:
            automation_share = st.slider(
                "Доля операций для автоматизации (%)",
                min_value=5,
                max_value=100,
                value=25,
                step=5,
            )

        with roi_col2:
            time_reduction = st.slider(
                "Сокращение времени (%)",
                min_value=5,
                max_value=90,
                value=30,
                step=5,
            )

        with roi_col3:
            hourly_cost = st.number_input(
                "Стоимость рабочего часа (руб.)",
                min_value=1,
                max_value=100000,
                value=500,
                step=100,
            )

        implementation_cost = st.number_input(
            "Условная стоимость внедрения (руб.)",
            min_value=0,
            max_value=100000000,
            value=150000,
            step=10000,
        )

        selected_days = max(
            (end_date - start_date).days + 1,
            1,
        )

        roi_result = calculate_automation_roi(
            completed_events=completed_events_count,
            average_duration_minutes=average_duration,
            automation_share_percent=automation_share,
            time_reduction_percent=time_reduction,
            hourly_cost=hourly_cost,
            selected_days=selected_days,
            implementation_cost=implementation_cost,
        )

        annual_hours_saved = roi_result["annual_hours_saved"]
        annual_savings = roi_result["annual_savings"]
        roi = roi_result["roi_percent"]
        payback_months = roi_result["payback_months"]

        st.divider()

        result_col1, result_col2, result_col3 = st.columns(3)

        result_col1.metric(
            "Potential time savings per year",
            f"{annual_hours_saved:,.1f} h".replace(",", " "),
        )

        result_col2.metric(
            "Potential annual savings",
            f"{annual_savings:,.0f} ₽".replace(",", " "),
        )

        if roi is not None:
            result_col3.metric(
                "Estimated ROI",
                f"{roi:.1f}%",
            )
        else:
            result_col3.metric(
                "Estimated ROI",
                "Not calculated",
            )

        if payback_months is not None:
            st.write(
                f"**Estimated payback period:** "
                f"{payback_months:.1f} months"
            )
        else:
            st.info(
                "Срок окупаемости не рассчитывается: "
                "нет положительной экономии или стоимость внедрения равна нулю."
            )

        st.info(
            "Это сценарная оценка, а не подтверждённый финансовый эффект. "
            "Расчёт предполагает, что высвобождённое рабочее время "
            "может быть использовано с экономической пользой. "
            "Он не учитывает расходы на поддержку, обучение, лицензии "
            "и возможные риски внедрения."
        )
    else:
        st.info("Нет доступных процессов для расчёта.")
else:
    st.info(
        "Для расчёта потенциального эффекта "
        "необходимы данные о бизнес-процессах."
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Business Process Analytics · Educational project · "
    "All records are synthetic and generated for demonstration."
)