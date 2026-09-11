"""Centralized environment configuration for both Lambda flows."""
from __future__ import annotations

import os


class Config:
    TRANSACTIONS_TABLE: str = os.environ["TRANSACTIONS_TABLE"]
    USERS_TABLE: str = os.environ["USERS_TABLE"]
    SNS_TOPIC_ARN: str = os.environ["SNS_TOPIC_ARN"]
    ANALYSIS_TABLE: str = os.environ.get("ANALYSIS_TABLE", "fraud-analysis")
    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "")
    LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "")
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "dev")

    SUSPICIOUS_HOUR_START: int = int(os.environ.get("SUSPICIOUS_HOUR_START", "2"))
    SUSPICIOUS_HOUR_END: int = int(os.environ.get("SUSPICIOUS_HOUR_END", "7"))
    VELOCITY_WINDOW_MINUTES: int = int(os.environ.get("VELOCITY_WINDOW_MINUTES", "2"))
    VELOCITY_MAX_TRANSACTIONS: int = int(os.environ.get("VELOCITY_MAX_TRANSACTIONS", "3"))