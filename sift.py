"""CLI entry point for SIFT with argparse, rich display, and three run modes."""

# must be set before any langchain imports to suppress duplicate output
import os
os.environ["LANGCHAIN_VERBOSE"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import argparse
import sys
import time

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from agent import app
from samples import SAMPLE_TICKETS

load_dotenv()

# cap output width so panels do not stretch on wide terminals
MAX_WIDTH = 90
terminal_width = os.get_terminal_size().columns
console = Console(
    width=min(terminal_width, MAX_WIDTH)
)

# cyan accent used by btop, lazydocker, and popular dev CLIs
ACCENT = "#00d4ff"
ACCENT_DIM = "#333333"
ACCENT_MID = "#006680"
ACCENT_SHADOW = "#005577"

PRIORITY_COLORS = {
    "P1 Critical": "bold color(160)",
    "P2 High": "bold color(208)",
    "P3 Medium": "bold color(178)",
    "P4 Low": "bold color(71)",
}

PRIORITY_LABELS = {
    "P1 Critical": "[color(160)]CRIT[/color(160)]",
    "P2 High": "[color(208)]HIGH[/color(208)]",
    "P3 Medium": "[color(178)]MED [/color(178)]",
    "P4 Low": "[color(71)]LOW [/color(71)]",
}

CATEGORY_COLORS = {
    "Networking": f"bold {ACCENT}",
    "Cloud Infrastructure": f"bold {ACCENT}",
    "Security": "bold color(160)",
    "Endpoint": f"bold {ACCENT}",
    "Identity": f"bold {ACCENT}",
    "Unknown": "bold color(245)",
}

CONFIDENCE_COLORS = {
    "High": "color(71)",
    "Medium": "color(178)",
    "Low": "color(160)",
}


def check_api_key() -> None:
    """Exit with a clear message if the OpenAI API key is not set."""
    if not os.environ.get("OPENAI_API_KEY"):
        console.print()
        console.print(
            Panel(
                "[bold color(160)]OPENAI_API_KEY"
                " is not set.[/bold color(160)]\n\n"
                "  [color(248)]1.[/color(248)]"
                " Copy .env.example to .env\n"
                "  [color(248)]2.[/color(248)]"
                " Add your OpenAI API key\n"
                "  [color(248)]3.[/color(248)]"
                " Run sift.py again",
                border_style="color(160)",
                padding=(1, 3),
            )
        )
        sys.exit(1)


def display_header() -> None:
    """Print the SIFT banner with layered depth effect."""
    console.print()

    # top rows: bright cyan for the main body
    # bottom rows: darker shade to create depth/shadow
    logo_lines = [
        f"[bold {ACCENT}]  ████████  ████  ████████  ████████████[/bold {ACCENT}]",
        f"[bold {ACCENT}]  ████      ████  ████          ████    [/bold {ACCENT}]",
        f"[bold {ACCENT}]  ████████  ████  ████████      ████    [/bold {ACCENT}]",
        f"[{ACCENT_SHADOW}]      ████  ████  ████          ████    [/{ACCENT_SHADOW}]",
        f"[{ACCENT_SHADOW}]  ████████  ████  ████          ████    [/{ACCENT_SHADOW}]",
    ]
    for line in logo_lines:
        console.print(line)

    console.print(
        f"  [{ACCENT_MID}]Autonomous IT Ticket"
        f" Triage Agent[/{ACCENT_MID}]"
    )
    console.print()
    console.print(Rule(style=ACCENT_DIM))
    console.print()


def display_result(state: dict) -> None:
    """Render the full triage result with panels and visual indicators."""
    # ticket
    console.print(
        Panel(
            f"[color(252)]{state['raw_ticket']}[/color(252)]",
            title=(
                f"[{ACCENT}] Ticket [/{ACCENT}]"
            ),
            title_align="left",
            border_style=ACCENT_DIM,
            padding=(1, 3),
        )
    )
    console.print()

    # result card
    cat = state["category"]
    pri = state["priority"]
    conf = state["confidence"]

    cat_color = CATEGORY_COLORS.get(cat, "bold color(245)")
    pri_color = PRIORITY_COLORS.get(pri, "bold white")
    pri_label = PRIORITY_LABELS.get(pri, pri)
    conf_color = CONFIDENCE_COLORS.get(conf, "color(245)")

    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        expand=True,
        show_edge=False,
    )
    table.add_column("L", style="color(245)", width=14)
    table.add_column("V")

    table.add_row(
        "  Category",
        f"[{cat_color}]{cat}[/{cat_color}]",
    )
    table.add_row("", "")
    table.add_row(
        "  Priority",
        f"{pri_label}  [{pri_color}]{pri}[/{pri_color}]",
    )
    table.add_row("", "")
    table.add_row(
        "  Confidence",
        f"[{conf_color}]{conf}[/{conf_color}]",
    )

    if state.get("priority_reason"):
        table.add_row("", "")
        table.add_row(
            "",
            f"[color(245)]{state['priority_reason']}"
            "[/color(245)]",
        )

    console.print(
        Panel(
            table,
            title=(
                f"[bold {ACCENT}] Result [/bold {ACCENT}]"
            ),
            title_align="left",
            border_style=ACCENT,
            padding=(1, 1),
        )
    )
    console.print()

    # diagnosis
    console.print(
        Panel(
            f"[color(252)]{state['diagnosis']}[/color(252)]",
            title=(
                f"[{ACCENT}] Diagnosis [/{ACCENT}]"
            ),
            title_align="left",
            border_style=ACCENT_DIM,
            padding=(1, 3),
        )
    )
    console.print()

    # resolution steps
    steps_lines = []
    for i, step in enumerate(state["resolution_steps"], 1):
        steps_lines.append(
            f"  [bold {ACCENT}]{i}.[/bold {ACCENT}]"
            f"  [color(252)]{step}[/color(252)]"
        )
    steps_text = "\n\n".join(steps_lines)

    console.print(
        Panel(
            steps_text,
            title=(
                f"[{ACCENT}] Actions [/{ACCENT}]"
            ),
            title_align="left",
            border_style=ACCENT_DIM,
            padding=(1, 3),
        )
    )
    console.print()

    # escalation
    if state["escalate"]:
        esc_content = (
            "[bold color(160)]"
            "ESCALATE  "
            "[/bold color(160)]"
            f"{state['escalation_reason']}"
        )
        esc_border = "color(160)"
    else:
        esc_content = (
            "[color(71)]No escalation required[/color(71)]"
        )
        esc_border = ACCENT_DIM

    console.print(
        Panel(
            f"  {esc_content}",
            title=(
                f"[{ACCENT}] Escalation [/{ACCENT}]"
            ),
            title_align="left",
            border_style=esc_border,
            padding=(1, 3),
        )
    )
    console.print()
    console.print(Rule(style=ACCENT_DIM))
    console.print()


def get_ticket_input() -> str:
    """Read multi line ticket text until the user enters a blank line."""
    console.print(
        f"  [bold color(252)]Enter your IT support ticket"
        " below[/bold color(252)]"
    )
    console.print(
        "  [color(245)]Press Enter twice when done[/color(245)]"
    )
    console.print()
    lines = []
    while True:
        try:
            line = input("  > ")
        except EOFError:
            break
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def run_triage(ticket_text: str) -> dict:
    """Invoke the LangGraph pipeline on a single ticket."""
    with console.status(
        f"[{ACCENT}]  Analyzing ticket...[/{ACCENT}]",
        spinner="dots",
        spinner_style=ACCENT,
    ):
        result = app.invoke({"raw_ticket": ticket_text})
    console.print()
    return result


def main() -> None:
    """Parse arguments and run in interactive, single, or demo mode."""
    parser = argparse.ArgumentParser(
        description="SIFT: Autonomous IT Ticket Triage Agent"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--ticket",
        type=str,
        help="Triage a single ticket provided as a string",
    )
    group.add_argument(
        "--demo",
        action="store_true",
        help="Run demo mode with sample tickets",
    )
    args = parser.parse_args()

    check_api_key()
    display_header()

    if args.ticket:
        result = run_triage(args.ticket)
        display_result(result)

    elif args.demo:
        for i, ticket in enumerate(SAMPLE_TICKETS[:5]):
            console.print(
                f"  [{ACCENT}]"
                f"Ticket {i + 1} of 5"
                f"[/{ACCENT}]"
            )
            console.print()
            result = run_triage(ticket)
            display_result(result)
            if i < 4:
                time.sleep(1)

    else:
        while True:
            ticket = get_ticket_input()
            if not ticket:
                console.print(
                    "  [color(178)]Empty ticket."
                    " Please try again.[/color(178)]\n"
                )
                continue
            console.print()
            result = run_triage(ticket)
            display_result(result)
            answer = input(
                "  Triage another ticket? (y/n): "
            ).strip()
            if answer.lower() != "y":
                console.print()
                break


if __name__ == "__main__":
    main()
