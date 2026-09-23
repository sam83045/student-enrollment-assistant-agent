"""Agent tools over mock data (FR-1..3, design §5).

Plain ``lookup_*`` functions hold the logic and are tested directly; the ``@tool``
wrappers expose them to the LLM with names and docstrings that match the spec.
"""

import re

from langchain_core.tools import tool

from enrollment_agent.data import APPLICANTS, DEADLINES, PROGRAMS

_FILLER_TOKENS = {"program", "programs", "degree", "degrees", "in", "of", "the", "a", "an", "all"}


def _tokens(text: str) -> list[str]:
    """Lowercase, drop periods/apostrophes, split on other punctuation, remove filler."""
    text = re.sub(r"[.'’]", "", text.lower())
    words = re.sub(r"[^a-z0-9]+", " ", text).split()
    return [w for w in words if w not in _FILLER_TOKENS]


def find_programs(query: str) -> list[str]:
    """Return the IDs of programs matching ``query`` (design §5.2)."""
    query_tokens = _tokens(query)
    if not query_tokens:
        return list(PROGRAMS)

    normalized = " ".join(query_tokens)
    exact, keyword = [], []
    for pid, program in PROGRAMS.items():
        names = [_tokens(name) for name in (program["program_name"], *program["aliases"])]
        if any(" ".join(name) == normalized for name in names):
            exact.append(pid)
        elif set(query_tokens) <= {token for name in names for token in name}:
            keyword.append(pid)
    return exact or keyword


def _program_not_found(program_name: str) -> dict:
    return {
        "error": "not_found",
        "message": f"No program matches '{program_name}'.",
        "available_programs": [p["program_name"] for p in PROGRAMS.values()],
    }


def _single_or_matches(records: list[dict]) -> dict:
    return records[0] if len(records) == 1 else {"matches": records}


def lookup_program(program_name: str) -> dict:
    """Program name, duration, tuition and prerequisites for matching programs."""
    ids = find_programs(program_name)
    if not ids:
        return _program_not_found(program_name)
    return _single_or_matches(
        [
            {
                "program_name": PROGRAMS[pid]["program_name"],
                "duration": PROGRAMS[pid]["duration"],
                "tuition": PROGRAMS[pid]["tuition"],
                "prerequisites": list(PROGRAMS[pid]["prerequisites"]),
            }
            for pid in ids
        ]
    )


def lookup_deadlines(program_name: str) -> dict:
    """Application, document and decision dates for matching programs."""
    ids = find_programs(program_name)
    if not ids:
        return _program_not_found(program_name)
    return _single_or_matches(
        [{"program_name": PROGRAMS[pid]["program_name"], **DEADLINES[pid]} for pid in ids]
    )


def lookup_application(applicant_id: str) -> dict:
    """Status record for one applicant; the ID is case- and whitespace-insensitive."""
    key = applicant_id.strip().upper()
    applicant = APPLICANTS.get(key)
    if applicant is None:
        return {
            "error": "not_found",
            "message": f"No application found with ID '{applicant_id}'.",
        }
    return {
        "applicant_id": key,
        "applicant_name": applicant["applicant_name"],
        "program": PROGRAMS[applicant["program_id"]]["program_name"],
        "status": applicant["status"],
        "next_step": applicant["next_step"],
        "missing_documents": list(applicant["missing_documents"]),
    }


@tool
def get_program_info(program_name: str) -> dict:
    """Look up university programs by name or subject keyword (e.g. "computer science", "MBA").

    Returns the program name, duration, tuition and prerequisites. If several programs
    match, returns {"matches": [...]}. Use "all programs" to list every program offered.
    If nothing matches, returns an error with the list of available programs.
    """
    return lookup_program(program_name)


@tool
def check_application_status(applicant_id: str) -> dict:
    """Check the status of a submitted application by applicant ID (e.g. "APP-1042").

    Returns the applicant name, program applied to, status ("Under Review", "Accepted",
    "Documents Pending" or "Rejected"), the next step, and any missing documents.
    """
    return lookup_application(applicant_id)


@tool
def get_deadlines(program_name: str) -> dict:
    """Get admission deadlines for a program by name or subject keyword.

    Returns the application deadline, document submission deadline and decision
    notification date (ISO dates). If several programs match, returns {"matches": [...]}.
    """
    return lookup_deadlines(program_name)


TOOLS = [get_program_info, check_application_status, get_deadlines]
