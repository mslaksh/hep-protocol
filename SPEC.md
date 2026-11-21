# Human Escalation Protocol (HEP) Specification — v0.1

## 1. Purpose
HEP defines a standard JSON message format and state machine for pausing an AI agent when confidence is low or a policy boundary is crossed, routing the decision to a human reviewer, and resuming execution safely.

## 2. Trigger Types
- `confidence`: Model/step confidence is strictly less than `threshold`.
- `policy`: A deterministic rule matched.
- `confidence_and_policy`: Both confidence and policy conditions fired simultaneously.
- `explicit`: The agent explicitly requested human input.

## 3. Interaction Modes
- `approve_reject`: Binary approval or rejection of `proposed_action`.
- `choose`: Reviewer selects one option from `interaction.options`.
- `edit`: Reviewer modifies fields listed in `interaction.editable_fields` before approval.
- `choose_or_edit`: Reviewer may pick an option and/or edit allowed fields.

## 4. Decision Values
- `approve`: Execute `proposed_action` unchanged.
- `edited_approve`: Execute `proposed_action` with `edited_arguments` applied.
- `reject`: Do not execute `proposed_action`.
- `timed_out`: Generated automatically when `now > sla.expires_at`.
