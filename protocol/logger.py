"""
logger.py
=========
Structured, colour-aware simulation logger.
Every component uses this to emit timestamped, labelled log lines so that
the simulation transcript is easy to read in a terminal.
"""

import time
import datetime


# ANSI colour codes (falls back gracefully in terminals without colour)
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
WHITE  = "\033[97m"
GREY   = "\033[90m"

COMPONENT_COLORS = {
    "SERVER"    : CYAN,
    "MIDDLEMAN" : YELLOW,
    "DATABASE"  : MAGENTA,
    "PROTOCOL"  : GREEN,
    "ERROR"     : RED,
    "SYSTEM"    : BLUE,
}


def _now() -> str:
    """Return wall-clock timestamp string."""
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _pad(label: str, width: int = 10) -> str:
    return label.ljust(width)


def log(component: str, message: str, level: str = "INFO") -> None:
    """
    Emit a formatted log line.

    Parameters
    ----------
    component : str   – Component name (SERVER / MIDDLEMAN / DATABASE / …)
    message   : str   – Human-readable event description
    level     : str   – INFO | WARN | ERROR | SUCCESS | STATE
    """
    color  = COMPONENT_COLORS.get(component.upper(), WHITE)
    ts     = GREY + _now() + RESET

    level_tag = {
        "INFO"   : f"{BLUE}[INFO   ]{RESET}",
        "WARN"   : f"{YELLOW}[WARN   ]{RESET}",
        "ERROR"  : f"{RED}[ERROR  ]{RESET}",
        "SUCCESS": f"{GREEN}[SUCCESS]{RESET}",
        "STATE"  : f"{MAGENTA}[STATE  ]{RESET}",
        "SIGNAL" : f"{CYAN}[SIGNAL ]{RESET}",
        "DATA"   : f"{WHITE}[DATA   ]{RESET}",
    }.get(level.upper(), f"[{level:7s}]")

    label = f"{color}{BOLD}{_pad(component)}{RESET}"
    print(f"  {ts}  {level_tag}  {label}  {message}")


def section(title: str) -> None:
    """Print a visual section separator."""
    bar = "─" * 72
    print(f"\n{BOLD}{GREEN}{bar}{RESET}")
    print(f"  {BOLD}{WHITE}◆  {title}{RESET}")
    print(f"{BOLD}{GREEN}{bar}{RESET}\n")


def subsection(title: str) -> None:
    """Print a lighter subsection header."""
    print(f"\n  {GREY}{'·'*60}{RESET}")
    print(f"  {BOLD}{GREY}▸ {title}{RESET}")
    print(f"  {GREY}{'·'*60}{RESET}\n")
