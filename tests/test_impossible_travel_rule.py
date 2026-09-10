from datetime import datetime, timezone

from src.rules.impossible_travel_rule import ImpossibleTravelRule


def test_should_flag_physically_impossible_travel(make_transaction):
    previous = make_transaction(
        occurred_at=datetime(2026, 9, 3, 17, 30, tzinfo=timezone.utc),
        latitude=-23.5505,
        longitude=-46.6333,
    )
    transaction = make_transaction(
        occurred_at=datetime(2026, 9, 3, 18, 30, tzinfo=timezone.utc),
        latitude=40.7128,
        longitude=-74.0060,
    )

    reason = ImpossibleTravelRule().evaluate(transaction, [previous])

    assert reason is not None
    assert "-40" in reason


def test_should_not_flag_travel_below_speed_threshold(make_transaction):
    previous = make_transaction(
        occurred_at=datetime(2026, 9, 3, 17, 30, tzinfo=timezone.utc),
        latitude=-23.5505,
        longitude=-46.6333,
    )
    transaction = make_transaction(
        occurred_at=datetime(2026, 9, 3, 18, 30, tzinfo=timezone.utc),
        latitude=-23.5600,
        longitude=-46.6400,
    )

    reason = ImpossibleTravelRule().evaluate(transaction, [previous])

    assert reason is None