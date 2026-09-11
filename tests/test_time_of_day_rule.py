from datetime import datetime, timezone

from src.scoring.rules.time_of_day_rule import TimeOfDayRule


def test_should_flag_transaction_when_inside_suspicious_window(make_transaction):
    rule = TimeOfDayRule(start_hour=2, end_hour=7)
    transaction = make_transaction(
        occurred_at=datetime(2026, 8, 20, 3, 30, tzinfo=timezone.utc)
    )

    reason = rule.evaluate(transaction, recent_history=[])

    assert reason is not None
    assert "03h" in reason


def test_should_not_flag_transaction_when_outside_suspicious_window(make_transaction):
    rule = TimeOfDayRule(start_hour=2, end_hour=7)
    transaction = make_transaction(
        occurred_at=datetime(2026, 8, 20, 14, 0, tzinfo=timezone.utc)
    )

    reason = rule.evaluate(transaction, recent_history=[])

    assert reason is None


def test_should_not_flag_transaction_at_exact_window_end_boundary(make_transaction):
    rule = TimeOfDayRule(start_hour=2, end_hour=7)
    transaction = make_transaction(
        occurred_at=datetime(2026, 8, 20, 7, 0, tzinfo=timezone.utc)
    )

    reason = rule.evaluate(transaction, recent_history=[])

    assert reason is None
