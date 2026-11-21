# HEP — Human Escalation Protocol (v0.1)

**A lightweight, framework-agnostic protocol for AI agents to pause, explain why they are uncertain, and hand off decisions cleanly to humans.**

---

## Why HEP?

Autonomous AI agents break down in production for two reasons:
1. They guess silently when confidence is low or policies are ambiguous.
2. Every framework invents a custom, tightly coupled way to ask a human—dumping raw text or blocking a terminal.

**HEP (Human Escalation Protocol)** separates **agent reasoning** from **human approval UIs**. Your agent emits one standardized `escalation.request` envelope with confidence signals, policy triggers, structured choices, editable arguments, and a timeout SLA. Any UI—CLI, Slack, web inbox, or mobile notification—can render it and return a structured `escalation.response`.

---

## Quickstart (30 Seconds)

### Install
```bash
cd python
pip install -e ".[dev]"
```

### Run the Interactive Demo
```bash
python ../examples/refund_agent.py
```

### Usage in Python
```python
from hep import EscalationEngine, PolicyRule, CLIAdapter, escalate

engine = EscalationEngine(
    agent_id="support-refund-agent",
    adapter=CLIAdapter(),
    rules=[
        PolicyRule(
            name="high_value_refund",
            condition=lambda args: args.get("amount_inr", 0) > 5000,
            reason="Refund exceeds ₹5,000 auto-approval limit",
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
        {"id": "reject", "label": "Reject request"},
    ],
    timeout_seconds=300,
    on_timeout="deny",
)
def issue_refund(order_id: str, amount_inr: int, *, _confidence: float = 1.0) -> dict:
    return {"status": "refunded", "order_id": order_id, "amount_inr": amount_inr}

# High confidence + within policy -> runs automatically
print(issue_refund("ORD-101", 1200, _confidence=0.96))

# Low confidence or > ₹5,000 -> pauses and escalates to human
print(issue_refund("ORD-7741", 6400, _confidence=0.62))
```

## License
MIT
