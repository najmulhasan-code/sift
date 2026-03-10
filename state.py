"""Shared state schema for the SIFT triage pipeline."""

from typing_extensions import TypedDict


class TicketState(TypedDict):
    """All fields that flow through the six node triage graph."""

    raw_ticket: str
    extracted_info: str
    category: str
    priority: str
    priority_reason: str
    diagnosis: str
    resolution_steps: list
    escalate: bool
    escalation_reason: str
    confidence: str
