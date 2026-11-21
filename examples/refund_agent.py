from hep import CLIAdapter, EscalationEngine, EscalationRejectedError, PolicyRule, escalate

engine = EscalationEngine(
    agent_id="support-refund-agent",
    adapter=CLIAdapter(),
    rules=[
        PolicyRule(
            name="high_value_refund",
            condition=lambda args: args.get("amount_inr", 0) > 5000,
            reason="Refund amount exceeds ₹5,000 auto-approval cap",
        )
    ],
)


@escalate(
    engine=engine,
    confidence_threshold=0.85,
    mode="choose_or_edit",
    editable_fields=["amount_inr"],
    options=[
        {"id": "approve_full", "label": "Approve requested refund"},
        {"id": "store_credit", "label": "Issue store credit instead"},
        {"id": "reject", "label": "Reject refund"},
    ],
)
def issue_refund(order_id: str, amount_inr: int) -> dict:
    return {"status": "refunded", "order_id": order_id, "amount_inr": amount_inr}


if __name__ == "__main__":
    print("1. Routine low-value refund (auto-approved):")
    print(issue_refund("ORD-101", 1200, _confidence=0.95))

    print("\n2. High-value + low-confidence refund (escalates to human):")
    try:
        result = issue_refund("ORD-7741", 6400, _confidence=0.62)
        print("Executed:", result)
    except EscalationRejectedError as exc:
        print("Halted:", exc)
