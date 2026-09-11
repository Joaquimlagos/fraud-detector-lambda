"""Access to users required by the scoring flow."""
from __future__ import annotations

import boto3

from src.shared.config import Config

_dynamodb = boto3.resource("dynamodb")


class UsersRepository:
    def __init__(self, table_name: str = Config.USERS_TABLE) -> None:
        self._table = _dynamodb.Table(table_name)

    def exists(self, user_id: str) -> bool:
        response = self._table.get_item(
            Key={"userId": user_id}, ProjectionExpression="userId", ConsistentRead=True
        )
        return "Item" in response