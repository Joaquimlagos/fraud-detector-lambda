"""Detects transactions that imply physically impossible travel speed."""
from __future__ import annotations

import math

from src.models.transaction_event import TransactionEvent
from src.rules.base import FraudRule


class ImpossibleTravelRule(FraudRule):
    def __init__(self, max_speed_kmh: float = 900.0) -> None:
        self._max_speed_kmh = max_speed_kmh

    def evaluate(
        self,
        transaction: TransactionEvent,
        recent_history: list[TransactionEvent],
    ) -> str | None:
        previous = _latest_transaction_before(transaction, recent_history)
        if previous is None or not _has_coordinates(transaction, previous):
            return None

        elapsed_hours = (
            transaction.occurred_at - previous.occurred_at
        ).total_seconds() / 3600
        if elapsed_hours <= 0:
            return None

        distance_km = _distance_km(
            previous.latitude,
            previous.longitude,
            transaction.latitude,
            transaction.longitude,
        )
        speed_kmh = distance_km / elapsed_hours
        if speed_kmh <= self._max_speed_kmh:
            return None

        return (
            "Impossible travel detected: implied speed is "
            f"{speed_kmh:.0f} km/h (-40)"
        )


def _latest_transaction_before(
    transaction: TransactionEvent,
    history: list[TransactionEvent],
) -> TransactionEvent | None:
    previous_transactions = [
        item for item in history if item.occurred_at < transaction.occurred_at
    ]
    return max(previous_transactions, key=lambda item: item.occurred_at, default=None)


def _has_coordinates(
    first: TransactionEvent, second: TransactionEvent
) -> bool:
    return all(
        value is not None
        for value in (
            first.latitude,
            first.longitude,
            second.latitude,
            second.longitude,
        )
    )


def _distance_km(
    latitude_one: float,
    longitude_one: float,
    latitude_two: float,
    longitude_two: float,
) -> float:
    earth_radius_km = 6371.0
    latitude_delta = math.radians(latitude_two - latitude_one)
    longitude_delta = math.radians(longitude_two - longitude_one)
    first = math.sin(latitude_delta / 2) ** 2
    second = (
        math.cos(math.radians(latitude_one))
        * math.cos(math.radians(latitude_two))
        * math.sin(longitude_delta / 2) ** 2
    )
    return earth_radius_km * 2 * math.atan2(math.sqrt(first + second), math.sqrt(1 - first - second))