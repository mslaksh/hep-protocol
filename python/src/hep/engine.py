from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .adapters import EscalationAdapter
from .models import (
    EscalationOption,
    EscalationRequest,
    EscalationResponse,
    InteractionSpec,
    ProposedAction,
    SLASpec,
    TriggerSpec,
)


class EscalationRejectedError(Exception):
    def __init__(self, request: EscalationRequest, response: EscalationResponse) -> None:
        self.request = request
        self.response = response
        super().__init__(
            f"Action '{request.proposed_action.tool}' rejected ({response.decision}): {response.note or 'No note'}"
        )


@dataclass
class PolicyRule:
    name: str
    condition: Callable[[dict[str, Any]], bool]
    reason: str


class EscalationEngine:
    def __init__(
        self,
        agent_id: str,
        adapter: EscalationAdapter,
        rules: list[PolicyRule] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.adapter = adapter
        self.rules = rules or []
        self.audit_log: list[dict[str, Any]] = []

    def evaluate_and_execute(
        self,
        fn: Callable[..., Any],
        bound_args: dict[str, Any],
        *,
        confidence: float | None = None,
        confidence_threshold: float | None = None,
        mode: str = "approve_reject",
        options: list[dict[str, str]] | None = None,
        editable_fields: list[str] | None = None,
        timeout_seconds: int = 300,
        on_timeout: str = "deny",
    ) -> Any:
        reasons: list[str] = []
        low_confidence = (
            confidence is not None
            and confidence_threshold is not None
            and confidence < confidence_threshold
        )
        if low_confidence:
            reasons.append(f"Confidence {confidence:.2f} is below threshold {confidence_threshold:.2f}")

        policy_triggered = False
        for rule in self.rules:
            if rule.condition(bound_args):
                policy_triggered = True
                reasons.append(rule.reason)

        if not reasons:
            return fn(**bound_args)

        if low_confidence and policy_triggered:
            trigger_type = "confidence_and_policy"
        elif low_confidence:
            trigger_type = "confidence"
        else:
            trigger_type = "policy"

        request = EscalationRequest(
            agent_id=self.agent_id,
            trigger=TriggerSpec(
                type=trigger_type,  # type: ignore[arg-type]
                confidence=confidence,
                threshold=confidence_threshold,
                reasons=reasons,
            ),
            proposed_action=ProposedAction(tool=fn.__name__, arguments=dict(bound_args)),
            interaction=InteractionSpec(
                mode=mode,  # type: ignore[arg-type]
                options=[EscalationOption(**o) for o in (options or [])],
                editable_fields=editable_fields or [],
            ),
            sla=SLASpec(
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds),
                on_timeout=on_timeout,  # type: ignore[arg-type]
            ),
        )

        response = self.adapter.request_decision(request)
        if response.escalation_id != request.escalation_id:
            raise ValueError("Mismatched escalation_id in EscalationResponse")

        now = datetime.now(timezone.utc)
        if now > request.sla.expires_at or response.decision == "timed_out":
            if request.sla.on_timeout == "proceed_with_flag":
                self.audit_log.append(
                    {"request": request.model_dump(mode="json"), "response": response.model_dump(mode="json"), "status": "unreviewed_timeout"}
                )
                return fn(**bound_args)
            timed_out_resp = EscalationResponse(
                escalation_id=request.escalation_id,
                decision="timed_out",
                note=f"Escalation expired; applied on_timeout={request.sla.on_timeout}",
            )
            self.audit_log.append(
                {"request": request.model_dump(mode="json"), "response": timed_out_resp.model_dump(mode="json"), "status": "rejected"}
            )
            raise EscalationRejectedError(request, timed_out_resp)

        if response.decision == "reject":
            self.audit_log.append(
                {"request": request.model_dump(mode="json"), "response": response.model_dump(mode="json"), "status": "rejected"}
            )
            raise EscalationRejectedError(request, response)

        final_args = dict(bound_args)
        if response.decision == "edited_approve" and response.edited_arguments:
            allowed = set(request.interaction.editable_fields)
            disallowed = set(response.edited_arguments.keys()) - allowed
            if disallowed:
                raise PermissionError(f"Reviewer attempted to edit non-editable fields: {sorted(disallowed)}")
            final_args.update(response.edited_arguments)

        self.audit_log.append(
            {"request": request.model_dump(mode="json"), "response": response.model_dump(mode="json"), "status": "approved"}
        )
        return fn(**final_args)


def escalate(
    engine: EscalationEngine,
    *,
    confidence_threshold: float | None = 0.85,
    mode: str = "approve_reject",
    options: list[dict[str, str]] | None = None,
    editable_fields: list[str] | None = None,
    timeout_seconds: int = 300,
    on_timeout: str = "deny",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            confidence = kwargs.pop("_confidence", None)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            return engine.evaluate_and_execute(
                fn,
                dict(bound.arguments),
                confidence=confidence,
                confidence_threshold=confidence_threshold,
                mode=mode,
                options=options,
                editable_fields=editable_fields,
                timeout_seconds=timeout_seconds,
                on_timeout=on_timeout,
            )

        return wrapper

    return decorator
