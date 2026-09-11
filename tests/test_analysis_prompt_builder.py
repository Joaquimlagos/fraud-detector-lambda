from src.analysis.prompt_builder import build_prompt
from src.analysis.retrieval.vector_search import SimilarCase
from src.shared.models.analysis_result import AnalysisResult


def test_prompt_contains_transaction_rules_and_similar_cases(make_transaction):
    transaction = make_transaction(transaction_id="txn-current", merchant="Shop")
    result = AnalysisResult.suspicious(["unusual transaction hour"])

    prompt = build_prompt(
        transaction,
        result,
        [SimilarCase(transaction_id="txn-history", similarity=0.92)],
    )

    assert '"transactionId": "txn-current"' in prompt
    assert "unusual transaction hour" in prompt
    assert '"transactionId": "txn-history"' in prompt
    assert "Do not invent facts" in prompt