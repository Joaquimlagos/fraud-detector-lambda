from src.analysis import handler as analysis_handler
from src.analysis.retrieval.vector_search import SimilarCase
from src.shared.models.analysis_result import AnalysisResult


class FakeRepository:
    def __init__(self, transaction):
        self.transaction = transaction

    def find_by_id(self, transaction_id):
        return self.transaction if transaction_id == self.transaction.transaction_id else None

    def find_result(self, transaction_id):
        return AnalysisResult.suspicious(["velocity threshold exceeded"])


class FakeCache:
    def __init__(self, cached=None):
        self.cached = cached
        self.saved = None

    def get(self, transaction_id):
        return self.cached

    def save(self, transaction_id, status, reasoning, similar_cases):
        self.saved = {
            "transactionId": transaction_id,
            "status": status,
            "reasoning": reasoning,
            "similarCases": similar_cases,
        }
        return self.saved


class FakeRetriever:
    def find_similar(self, transaction):
        return [SimilarCase("txn-old", 0.88)]


class FakeLLM:
    def generate(self, prompt):
        assert "velocity threshold exceeded" in prompt
        return "The transaction matches a velocity rule alert."


def test_handler_generates_and_saves_investigation(make_transaction):
    cache = FakeCache()
    response = analysis_handler.handler(
        {"transactionId": "txn-1"},
        None,
        cache=cache,
        retriever=FakeRetriever(),
        llm_client=FakeLLM(),
        repository=FakeRepository(make_transaction()),
    )

    assert response == {
        "transactionId": "txn-1",
        "status": "suspicious",
        "reasoning": "The transaction matches a velocity rule alert.",
        "cached": False,
    }
    assert cache.saved["status"] == "SUSPICIOUS"


def test_handler_returns_cached_investigation_without_calling_llm(make_transaction):
    cached = {
        "transactionId": "txn-1",
        "status": "SUSPICIOUS",
        "reasoning": "Previously generated",
        "similarCases": [],
    }
    response = analysis_handler.handler(
        {"transactionId": "txn-1"},
        None,
        cache=FakeCache(cached),
        llm_client=FakeLLM(),
        repository=FakeRepository(make_transaction()),
    )

    assert response["cached"] is True
    assert response["reasoning"] == "Previously generated"


def test_handler_returns_structured_error_for_invalid_payload():
    response = analysis_handler.handler({}, None)

    assert response["status"] == "error"
    assert "similarCases" not in response