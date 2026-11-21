from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from .models import EscalationRequest, EscalationResponse, ReviewerInfo


class EscalationAdapter(ABC):
    @abstractmethod
    def request_decision(self, request: EscalationRequest) -> EscalationResponse:
        raise NotImplementedError


class AutoDecisionAdapter(EscalationAdapter):
    def __init__(
        self,
        decision: str = "approve",
        edited_arguments: dict[str, Any] | None = None,
        selected_option: str | None = None,
        reviewer_id: str = "auto-reviewer",
        note: str | None = None,
    ) -> None:
        self.decision = decision
        self.edited_arguments = edited_arguments
        self.selected_option = selected_option
        self.reviewer_id = reviewer_id
        self.note = note

    def request_decision(self, request: EscalationRequest) -> EscalationResponse:
        return EscalationResponse(
            escalation_id=request.escalation_id,
            decision=self.decision,  # type: ignore[arg-type]
            edited_arguments=self.edited_arguments,
            selected_option=self.selected_option,
            reviewer=ReviewerInfo(id=self.reviewer_id, role="automated"),
            note=self.note,
        )


class CLIAdapter(EscalationAdapter):
    def request_decision(self, request: EscalationRequest) -> EscalationResponse:
        print("\n" + "=" * 60)
        print(f"HUMAN ESCALATION REQUIRED [{request.escalation_id}]")
        print(f"Agent   : {request.agent_id}")
        print(f"Tool    : {request.proposed_action.tool}")
        print(f"Args    : {json.dumps(request.proposed_action.arguments)}")
        print("Reasons :")
        for reason in request.trigger.reasons:
            print(f"  - {reason}")
        if request.interaction.options:
            print("Options :")
            for idx, opt in enumerate(request.interaction.options, start=1):
                print(f"  {idx}. [{opt.id}] {opt.label}")
        print("=" * 60)

        choice = input("Decision [a=approve, e=edit, r=reject]: ").strip().lower()
        if choice == "r":
            note = input("Rejection note (optional): ").strip() or None
            return EscalationResponse(
                escalation_id=request.escalation_id,
                decision="reject",
                reviewer=ReviewerInfo(id="cli-user", role="operator"),
                note=note,
            )

        edited: dict[str, Any] = {}
        if choice == "e" and request.interaction.editable_fields:
            for field in request.interaction.editable_fields:
                current = request.proposed_action.arguments.get(field)
                raw = input(f"New value for '{field}' (current={current!r}, Enter to keep): ").strip()
                if raw:
                    edited[field] = type(current)(raw) if current is not None else raw

        if edited:
            return EscalationResponse(
                escalation_id=request.escalation_id,
                decision="edited_approve",
                edited_arguments=edited,
                reviewer=ReviewerInfo(id="cli-user", role="operator"),
            )

        return EscalationResponse(
            escalation_id=request.escalation_id,
            decision="approve",
            reviewer=ReviewerInfo(id="cli-user", role="operator"),
        )
