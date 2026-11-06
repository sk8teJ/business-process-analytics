import pytest

from app.metrics import calculate_automation_roi, calculate_return_rate


def test_return_rate_counts_orders_not_return_requests():
    assert calculate_return_rate(12, 100) == pytest.approx(12.0)


def test_return_rate_with_no_orders_is_zero():
    assert calculate_return_rate(0, 0) == 0.0


def test_return_rate_rejects_negative_counts():
    with pytest.raises(ValueError):
        calculate_return_rate(-1, 10)


def test_automation_roi_uses_completed_events_and_annualizes_period():
    result = calculate_automation_roi(
        completed_events=100,
        average_duration_minutes=30,
        automation_share_percent=50,
        time_reduction_percent=20,
        hourly_cost=600,
        selected_days=30,
        implementation_cost=10000,
    )

    assert result["hours_saved_in_period"] == pytest.approx(5.0)
    assert result["savings_in_period"] == pytest.approx(3000.0)
    assert result["annual_hours_saved"] == pytest.approx(5 * 365 / 30)
    assert result["annual_savings"] == pytest.approx(3000 * 365 / 30)
    assert result["roi_percent"] == pytest.approx(265.0)
    assert result["payback_months"] == pytest.approx(10000 / (3000 * 365 / 30) * 12)


def test_automation_roi_handles_no_completed_events():
    result = calculate_automation_roi(
        completed_events=0,
        average_duration_minutes=0,
        automation_share_percent=25,
        time_reduction_percent=30,
        hourly_cost=500,
        selected_days=365,
        implementation_cost=10000,
    )

    assert result["annual_hours_saved"] == 0
    assert result["annual_savings"] == 0
    assert result["roi_percent"] == -100
    assert result["payback_months"] is None


def test_automation_roi_requires_positive_period():
    with pytest.raises(ValueError):
        calculate_automation_roi(
            completed_events=1,
            average_duration_minutes=10,
            automation_share_percent=25,
            time_reduction_percent=30,
            hourly_cost=500,
            selected_days=0,
            implementation_cost=10000,
        )
