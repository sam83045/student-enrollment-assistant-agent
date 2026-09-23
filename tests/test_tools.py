"""T-03..T-05: program matching, lookup functions and LangChain tool wrappers (FR-1..3)."""

import pytest

from enrollment_agent.data import PROGRAMS
from enrollment_agent.tools import (
    TOOLS,
    check_application_status,
    find_programs,
    get_deadlines,
    get_program_info,
    lookup_application,
    lookup_deadlines,
    lookup_program,
)

ALL_PROGRAM_IDS = set(PROGRAMS)


# --- T-03: matching -------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        ("M.S. Computer Science", {"ms-cs"}),
        ("m.s. computer science", {"ms-cs"}),
        ("B.S. Computer Science", {"bs-cs"}),
        ("computer science", {"bs-cs", "ms-cs"}),
        ("Computer Science programs", {"bs-cs", "ms-cs"}),
        ("  COMPUTER   science!! ", {"bs-cs", "ms-cs"}),
        ("cs", {"bs-cs", "ms-cs"}),
        ("MBA", {"mba"}),
        ("business administration", {"mba"}),
        ("Master of Business Administration", {"mba"}),
        ("mechanical engineering", {"bs-me"}),
        ("master's in computer science", {"ms-cs"}),
    ],
)
def test_find_programs_matches(query, expected):
    assert set(find_programs(query)) == expected


@pytest.mark.parametrize("query", ["programs", "all programs", "all", "  "])
def test_find_programs_generic_query_returns_all(query):
    assert set(find_programs(query)) == ALL_PROGRAM_IDS


@pytest.mark.parametrize("query", ["art history", "computer art", "xyz"])
def test_find_programs_no_match(query):
    assert find_programs(query) == []


# --- T-04: lookup functions ----------------------------------------------


def test_lookup_program_single_match_is_flat_dict():  # AC-1.1
    result = lookup_program("M.S. Computer Science")
    assert result == {
        "program_name": "M.S. Computer Science",
        "duration": PROGRAMS["ms-cs"]["duration"],
        "tuition": PROGRAMS["ms-cs"]["tuition"],
        "prerequisites": PROGRAMS["ms-cs"]["prerequisites"],
    }


def test_lookup_program_multiple_matches():  # AC-1.2
    result = lookup_program("computer science")
    names = {m["program_name"] for m in result["matches"]}
    assert names == {"B.S. Computer Science", "M.S. Computer Science"}
    for match in result["matches"]:
        assert set(match) == {"program_name", "duration", "tuition", "prerequisites"}


def test_lookup_program_not_found():  # AC-1.3
    result = lookup_program("art history")
    assert result["error"] == "not_found"
    assert "art history" in result["message"]
    assert set(result["available_programs"]) == {p["program_name"] for p in PROGRAMS.values()}


def test_lookup_program_returns_copies():
    lookup_program("MBA")["prerequisites"].append("mutated")
    assert "mutated" not in PROGRAMS["mba"]["prerequisites"]


def test_lookup_deadlines_single_match():  # AC-3.1
    result = lookup_deadlines("MBA")
    assert result == {
        "program_name": "Master of Business Administration",
        "application_deadline": "2027-03-01",
        "document_submission_deadline": "2027-03-15",
        "decision_notification_date": "2027-05-01",
    }


def test_lookup_deadlines_multiple_matches():  # AC-3.1
    result = lookup_deadlines("computer science")
    assert {m["program_name"] for m in result["matches"]} == {
        "B.S. Computer Science",
        "M.S. Computer Science",
    }


def test_lookup_deadlines_not_found():  # AC-3.1
    result = lookup_deadlines("art history")
    assert result["error"] == "not_found"
    assert result["available_programs"]


def test_lookup_application_found():  # AC-2.1
    result = lookup_application("APP-1042")
    assert result == {
        "applicant_id": "APP-1042",
        "applicant_name": "Jordan Lee",
        "program": "M.S. Computer Science",
        "status": "Documents Pending",
        "next_step": "Submit missing documents by 2027-02-15",
        "missing_documents": ["Official transcripts", "Two letters of recommendation"],
    }


@pytest.mark.parametrize("applicant_id", ["app-1042", "  APP-1042 ", "App-1042"])
def test_lookup_application_id_is_normalized(applicant_id):  # AC-2.1
    assert lookup_application(applicant_id)["applicant_id"] == "APP-1042"


def test_lookup_application_no_missing_documents_is_empty_list():
    assert lookup_application("APP-1044")["missing_documents"] == []


def test_lookup_application_not_found():  # AC-2.3
    result = lookup_application("APP-9999")
    assert result["error"] == "not_found"
    assert "APP-9999" in result["message"]


# --- T-05: LangChain tool wrappers ---------------------------------------


def test_tool_names_match_spec():
    assert [t.name for t in TOOLS] == [
        "get_program_info",
        "check_application_status",
        "get_deadlines",
    ]


@pytest.mark.parametrize(
    "tool_obj, arg",
    [
        (get_program_info, "program_name"),
        (check_application_status, "applicant_id"),
        (get_deadlines, "program_name"),
    ],
)
def test_tool_schema_has_single_string_argument(tool_obj, arg):
    schema = tool_obj.tool_call_schema.model_json_schema()
    assert list(schema["properties"]) == [arg]
    assert schema["properties"][arg]["type"] == "string"
    assert schema["required"] == [arg]
    assert tool_obj.description


def test_tools_invoke_same_as_lookups():
    assert get_program_info.invoke({"program_name": "cs"}) == lookup_program("cs")
    assert get_deadlines.invoke({"program_name": "MBA"}) == lookup_deadlines("MBA")
    assert check_application_status.invoke({"applicant_id": "app-1043"}) == lookup_application(
        "app-1043"
    )
