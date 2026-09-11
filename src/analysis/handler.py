"""Direct-invocation entry point for investigative transaction analysis."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from src.analysis.cache import AnalysisCache
from src.analysis.llm_client import LLMClient
from src.analysis.prompt_builder import build_prompt
from src.analysis.retrieval.vector_search import SimilarCase, VectorSearch
from src.shared.repository.transactions_repository import TransactionsRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class _Retriever(Protocol):
    def find_similar(self, transaction: Any) -> list[SimilarCase]: ...


class _Generator(Protocol):
    def generate(self, prompt: str) -> str: ...


_repository = TransactionsRepository()
_cache = AnalysisCache()
_retriever = VectorSearch(_repository)
_llm_client = LLMClient()


def handler(
    event: dict[str, Any],
    context: object,
    cache: AnalysisCache | None = None,
    retriever: _Retriever | None = None,
    llm_client: _Generator | None = None,
    repository: TransactionsRepository | None = None,
) -> dict[str, Any]:
    transaction_id = event.get("transactionId") if isinstance(event, dict) else None
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        return _error_response("transactionId is required")

    active_cache = cache or _cache
    cached = active_cache.get(transaction_id)
    if cached:
        return _response_from_analysis(cached, cached=True)

    try:
        active_repository = repository or _repository
        transaction = active_repository.find_by_id(transaction_id)
        if transaction is None:
            return _error_response(f"Transaction {transaction_id} was not found", transaction_id)

        similar_cases = (retriever or _retriever).find_similar(transaction)
        scoring_result = active_repository.find_result(transaction_id)
        prompt = build_prompt(transaction, scoring_result, similar_cases)
        reasoning = (llm_client or _llm_client).generate(prompt)
        status = scoring_result.status.value if scoring_result else "UNKNOWN"
        saved = active_cache.save(
            transaction_id,
            status,
            reasoning,
            [case.to_dict() for case in similar_cases],
        )
        return _response_from_analysis(saved, cached=False)
    except Exception as error:
        logger.exception("Investigation analysis failed for transaction %s", transaction_id)
        return _error_response(str(error), transaction_id)


def _response_from_analysis(item: dict[str, Any], cached: bool) -> dict[str, Any]:
    return {
        "transactionId": item["transactionId"],
        "status": str(item.get("status", "UNKNOWN")).lower(),
        "reasoning": str(item.get("reasoning", "")),
        "cached": cached,
    }


def _error_response(message: str, transaction_id: str | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {
        "status": "error",
        "error": message,
        "reasoning": "",
        "cached": False,
    }
    if transaction_id:
        response["transactionId"] = transaction_id
    return response