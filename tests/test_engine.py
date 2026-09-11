from src.shared.models.analysis_result import TransactionStatus
from src.scoring.rules.base import FraudRule
from src.scoring.rules.engine import AnalysisEngine


class _AlwaysTriggersRule(FraudRule):
    def evaluate(self, transaction, recent_history):
        return "always triggers"


class _NeverTriggersRule(FraudRule):
    def evaluate(self, transaction, recent_history):
        return None


def test_should_approve_when_no_rule_triggers(make_transaction):
    engine = AnalysisEngine(rules=[_NeverTriggersRule(), _NeverTriggersRule()])

    result = engine.analyze(make_transaction(), recent_history=[])

    assert result.status is TransactionStatus.APPROVED
    assert result.reasons == []


def test_should_flag_suspicious_when_any_rule_triggers(make_transaction):
    engine = AnalysisEngine(rules=[_NeverTriggersRule(), _AlwaysTriggersRule()])

    result = engine.analyze(make_transaction(), recent_history=[])

    assert result.status is TransactionStatus.SUSPICIOUS
    assert result.reasons == ["always triggers"]


def test_should_aggregate_reasons_from_multiple_triggered_rules(make_transaction):
    engine = AnalysisEngine(rules=[_AlwaysTriggersRule(), _AlwaysTriggersRule()])

    result = engine.analyze(make_transaction(), recent_history=[])

    assert len(result.reasons) == 2
