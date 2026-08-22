from src.rules.velocity_rule import VelocityRule


def test_should_flag_transaction_when_history_exceeds_limit(make_transaction):
    rule = VelocityRule(max_transactions=3, window_minutes=2)
    transaction = make_transaction()
    # 3 no histórico + a atual = 4, acima do limite de 3
    history = [make_transaction(transaction_id=f"txn-{i}") for i in range(3)]

    reason = rule.evaluate(transaction, recent_history=history)

    assert reason is not None
    assert "4 transactions" in reason


def test_should_not_flag_transaction_when_history_within_limit(make_transaction):
    rule = VelocityRule(max_transactions=3, window_minutes=2)
    transaction = make_transaction()
    # 1 no histórico + a atual = 2, dentro do limite de 3
    history = [make_transaction(transaction_id="txn-0")]

    reason = rule.evaluate(transaction, recent_history=history)

    assert reason is None


def test_should_not_flag_transaction_when_history_is_empty(make_transaction):
    rule = VelocityRule(max_transactions=3, window_minutes=2)
    transaction = make_transaction()

    reason = rule.evaluate(transaction, recent_history=[])

    assert reason is None
