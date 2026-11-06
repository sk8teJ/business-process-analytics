"""Pure calculation helpers for dashboard business metrics."""


def calculate_return_rate(returned_orders: int, total_orders: int) -> float:
    """Return the percentage of orders with at least one return request."""
    if returned_orders < 0 or total_orders < 0:
        raise ValueError("Order counts cannot be negative.")
    if total_orders == 0:
        return 0.0
    return returned_orders / total_orders * 100


def calculate_automation_roi(
    *,
    completed_events: int,
    average_duration_minutes: float,
    automation_share_percent: float,
    time_reduction_percent: float,
    hourly_cost: float,
    selected_days: int,
    implementation_cost: float,
) -> dict[str, float | None]:
    """Estimate annualized savings from completed process events.

    This is a scenario model, not a measured financial result. The selected
    period is annualized using a 365-day year.
    """
    if completed_events < 0:
        raise ValueError("Completed event count cannot be negative.")
    if average_duration_minutes < 0 or hourly_cost < 0 or implementation_cost < 0:
        raise ValueError("Duration and monetary values cannot be negative.")
    if not 0 <= automation_share_percent <= 100:
        raise ValueError("Automation share must be between 0 and 100.")
    if not 0 <= time_reduction_percent <= 100:
        raise ValueError("Time reduction must be between 0 and 100.")
    if selected_days <= 0:
        raise ValueError("Selected period must contain at least one day.")

    hours_saved_in_period = (
        completed_events
        * average_duration_minutes
        / 60
        * automation_share_percent / 100
        * time_reduction_percent / 100
    )
    savings_in_period = hours_saved_in_period * hourly_cost
    annualization_factor = 365 / selected_days
    annual_hours_saved = hours_saved_in_period * annualization_factor
    annual_savings = savings_in_period * annualization_factor

    roi_percent = None
    payback_months = None
    if implementation_cost > 0:
        roi_percent = (
            (annual_savings - implementation_cost)
            / implementation_cost
            * 100
        )
        if annual_savings > 0:
            payback_months = implementation_cost / annual_savings * 12

    return {
        "hours_saved_in_period": hours_saved_in_period,
        "savings_in_period": savings_in_period,
        "annual_hours_saved": annual_hours_saved,
        "annual_savings": annual_savings,
        "roi_percent": roi_percent,
        "payback_months": payback_months,
    }
