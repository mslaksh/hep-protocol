import pytest
from hep import AutoDecisionAdapter, EscalationEngine, EscalationRejectedError, PolicyRule, escalate


def test_auto_executes_when_confident_and_within_policy():
    adapter = AutoDecisionAdapter(decision="reject")
    engine = EscalationEngine("test-agent", adapter=adapter)

    @escalate(engine=engine, confidence_threshold=0.8)
    def transfer(amount: int) -> int:
        return amount

    assert transfer(100, _confidence=0.95) == 100
    assert engine.audit_log == []


def test_escalates_and_applies_edited_arguments():
    adapter = AutoDecisionAdapter(decision="edited_approve", edited_arguments={"amount": 2500})
    engine = EscalationEngine(
        "test-agent",
        adapter=adapter,
        rules=[PolicyRule("cap", lambda a: a["amount"] > 5000, "Over cap")],
    )

    @escalate(engine=engine, confidence_threshold=0.8, mode="edit", editable_fields=["amount"])
    def transfer(amount: int) -> int:
        return amount

    assert transfer(6000, _confidence=0.9) == 2500
    assert engine.audit_log[0]["status"] == "approved"


def test_blocks_editing_unlisted_fields():
    adapter = AutoDecisionAdapter(decision="edited_approve", edited_arguments={"account": "attacker"})
    engine = EscalationEngine("test-agent", adapter=adapter)

    @escalate(engine=engine, confidence_threshold=0.8, mode="edit", editable_fields=["amount"])
    def transfer(account: str, amount: int) -> str:
        return f"{account}:{amount}"

    with pytest.raises(PermissionError):
        transfer("user-1", 500, _confidence=0.4)


def test_rejection_raises_error():
    adapter = AutoDecisionAdapter(decision="reject", note="Outside return window")
    engine = EscalationEngine("test-agent", adapter=adapter)

    @escalate(engine=engine, confidence_threshold=0.8)
    def refund(order_id: str) -> str:
        return order_id

    with pytest.raises(EscalationRejectedError):
        refund("ORD-9", _confidence=0.5)
