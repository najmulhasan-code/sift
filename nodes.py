"""Six triage node functions that each call GPT 4o and return partial state."""

import re
import sys

import openai
from dotenv import load_dotenv
from rich.console import Console

from state import TicketState

load_dotenv()

client = openai.OpenAI()
console = Console(stderr=True)


def _call_openai(messages: list, temperature: float = 0) -> str:
    """Send messages to GPT 4o and return the content string."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=temperature,
            messages=messages,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        console.print(
            f"[bold red]OpenAI API error:[/bold red] {exc}"
        )
        sys.exit(1)


# node 1 of 6: pull structured details from raw ticket text
def extract(state: TicketState) -> dict:
    """Extract key technical details from the raw ticket text."""
    system = (
        "You are an IT support triage specialist. Extract the key"
        " technical details from this support ticket: what system is"
        " affected, what the reported behavior is, any error messages"
        " mentioned, and any urgency signals. Return only the extracted"
        " summary, nothing else."
    )
    result = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": state["raw_ticket"]},
    ])
    return {"extracted_info": result}


# node 2 of 6: assign one of six category labels
def classify(state: TicketState) -> dict:
    """Classify the ticket into one of six category strings."""
    system = (
        "You are an IT support classifier. Based on the extracted"
        " ticket details below, classify this ticket into exactly one"
        " of these categories:\n\n"
        "Networking: VPN, DNS, firewall, network outage, connectivity,"
        " Wi Fi, routing\n"
        "Cloud Infrastructure: AWS, Azure, GCP, VM, storage, backup,"
        " cloud access, SaaS down\n"
        "Security: malware, ransomware, phishing, suspicious login,"
        " unauthorized access, account compromise, virus, breach\n"
        "Endpoint: laptop, desktop, printer, software install, OS"
        " update, hardware failure\n"
        "Identity: password reset, MFA, account locked, new user,"
        " permissions, access denied\n"
        "Unknown: if the ticket does not clearly fit any of the above\n\n"
        "Respond with exactly one category name, nothing else."
    )
    result = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": state["extracted_info"]},
    ])
    return {"category": result}


# node 3 of 6: assign priority based on category and urgency signals
def prioritize(state: TicketState) -> dict:
    """Assign a priority level and one sentence justification."""
    system = (
        "You are an IT support priority analyst. Based on the ticket"
        " details and category, assign a priority level using these"
        " rules:\n\n"
        "P1 Critical: full outage, ransomware, active breach, entire"
        " office offline\n"
        "P2 High: single user cannot work, security alert requiring"
        " immediate action, production system degraded\n"
        "P3 Medium: performance issue, non critical system down,"
        " scheduled task failing\n"
        "P4 Low: how to question, minor inconvenience, information"
        " request\n\n"
        "Respond with exactly two lines.\n"
        "Line 1: the priority level (for example: P1 Critical)\n"
        "Line 2: one sentence explaining why this priority was assigned"
    )
    user_content = (
        f"Category: {state['category']}\n\n"
        f"Details: {state['extracted_info']}"
    )
    result = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ])
    lines = result.strip().splitlines()
    priority = lines[0].strip() if lines else "P3 Medium"
    reason = lines[1].strip() if len(lines) > 1 else ""
    return {"priority": priority, "priority_reason": reason}


# node 4 of 6: write a technical diagnosis for handoff
def diagnose(state: TicketState) -> dict:
    """Produce a 2 to 3 sentence technical diagnosis."""
    system = (
        "You are a senior IT technician. Write a 2 to 3 sentence"
        " technical diagnosis explaining the likely root cause of"
        " this issue. Write as if you are handing off the ticket to"
        " a junior technician. Be specific and technical."
    )
    user_content = (
        f"Category: {state['category']}\n\n"
        f"Details: {state['extracted_info']}"
    )
    result = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ])
    return {"diagnosis": result}


# node 5 of 6: generate concrete resolution steps
def resolve(state: TicketState) -> dict:
    """Generate 4 to 7 actionable resolution steps as a list."""
    system = (
        "You are an IT resolution specialist. Generate 4 to 7"
        " specific, actionable resolution steps for this issue."
        " Each step must be concrete and technical, not generic."
        " Return the steps as a numbered list with one step per"
        " line, each starting with a number and a period."
    )
    user_content = (
        f"Category: {state['category']}\n"
        f"Priority: {state['priority']}\n\n"
        f"Diagnosis: {state['diagnosis']}"
    )
    # temperature 0.2 because resolution phrasing benefits from slight variation
    result = _call_openai(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    # gpt 4o returns steps as numbered text; parse into a clean list
    steps = []
    for line in result.strip().splitlines():
        cleaned = re.sub(r"^\d+\.\s*", "", line.strip())
        if cleaned:
            steps.append(cleaned)
    return {"resolution_steps": steps}


# node 6 of 6: decide on escalation and confidence
def evaluate(state: TicketState) -> dict:
    """Decide whether to escalate and assess triage confidence."""
    system = (
        "You are an IT escalation analyst. Based on the full triage"
        " below, make two decisions.\n\n"
        "Decision 1: Should this ticket be escalated to a human"
        " technician? Answer ESCALATE if any of these are true:\n"
        "  Active ransomware or breach is suspected\n"
        "  The issue affects more than 10 users simultaneously\n"
        "  The triage confidence is Low\n"
        "  The ticket involves regulatory compliance or data loss\n"
        "Otherwise answer NO ESCALATE.\n\n"
        "Decision 2: What is the confidence level?\n"
        "  High if the category is clear and resolution steps are"
        " specific\n"
        "  Medium if the category required inference\n"
        "  Low if the ticket text was ambiguous or incomplete\n\n"
        "Respond with exactly three lines.\n"
        "Line 1: ESCALATE or NO ESCALATE\n"
        "Line 2: one sentence reason for escalation, or none if no"
        " escalation\n"
        "Line 3: High, Medium, or Low"
    )
    user_content = (
        f"Category: {state['category']}\n"
        f"Priority: {state['priority']}\n"
        f"Diagnosis: {state['diagnosis']}\n"
        f"Steps: {state['resolution_steps']}"
    )
    result = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ])
    lines = result.strip().splitlines()
    escalate_line = lines[0].strip().upper() if lines else "NO ESCALATE"
    escalate = "ESCALATE" in escalate_line and "NO" not in escalate_line
    reason = lines[1].strip() if len(lines) > 1 else ""
    if not escalate:
        reason = ""
    confidence = lines[2].strip() if len(lines) > 2 else "Medium"
    return {
        "escalate": escalate,
        "escalation_reason": reason,
        "confidence": confidence,
    }
