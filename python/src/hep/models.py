from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TriggerSpec(BaseModel):
    type: Literal["confidence", "policy", "confidence_and_policy", "explicit"]
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    reasons: list[str] = Field(min_length=1)


class ProposedAction(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class EscalationOption(BaseModel):
    id: str
    label: str


class InteractionSpec(BaseModel):
    mode: Literal["approve_reject", "choose", "edit", "choose_or_edit"] = "approve_reject"
    options: list[EscalationOption] = Field(default_factory=list)
    editable_fields: list[str] = Field(default_factory=list)


class SLASpec(BaseModel):
    expires_at: datetime
    on_timeout: Literal["deny", "escalate_up", "proceed_with_flag"] = "deny"


class EscalationRequest(BaseModel):
    protocol: Literal["hep/0.1"] = "hep/0.1"
    escalation_id: str = Field(default_factory=lambda: f"esc_{uuid4().hex[:8]}")
    agent_id: str
    trigger: TriggerSpec
    proposed_action: ProposedAction
    interaction: InteractionSpec = Field(default_factory=InteractionSpec)
    sla: SLASpec


class ReviewerInfo(BaseModel):
    id: str
    role: str = "reviewer"


class EscalationResponse(BaseModel):
    protocol: Literal["hep/0.1"] = "hep/0.1"
    escalation_id: str
    decision: Literal["approve", "edited_approve", "reject", "timed_out"]
    selected_option: str | None = None
    edited_arguments: dict[str, Any] | None = None
    reviewer: ReviewerInfo | None = None
    note: str | None = None
