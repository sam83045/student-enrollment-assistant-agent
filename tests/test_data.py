"""T-02: mock data integrity (FR-4)."""

from enrollment_agent.data import APPLICANTS, DEADLINES, PROGRAMS, VALID_STATUSES


def test_at_least_three_programs_including_computer_science():  # AC-4.1
    assert len(PROGRAMS) >= 3
    assert any("Computer Science" in p["program_name"] for p in PROGRAMS.values())


def test_programs_have_required_fields():
    for program in PROGRAMS.values():
        assert program["program_name"]
        assert program["duration"]
        assert program["tuition"]
        assert isinstance(program["prerequisites"], list) and program["prerequisites"]
        assert isinstance(program["aliases"], list)


def test_at_least_three_applicants():  # AC-4.2
    assert len(APPLICANTS) >= 3


def test_app_1042_has_pending_documents():  # AC-4.2
    applicant = APPLICANTS["APP-1042"]
    assert applicant["status"] == "Documents Pending"
    assert applicant["missing_documents"]


def test_every_program_has_deadlines():  # AC-4.3
    assert set(DEADLINES) == set(PROGRAMS)
    for deadlines in DEADLINES.values():
        assert deadlines["application_deadline"]
        assert deadlines["document_submission_deadline"]
        assert deadlines["decision_notification_date"]


def test_every_applicant_references_an_existing_program():  # AC-4.3
    for applicant in APPLICANTS.values():
        assert applicant["program_id"] in PROGRAMS


def test_applicant_statuses_are_valid():  # AC-2.2
    for applicant in APPLICANTS.values():
        assert applicant["status"] in VALID_STATUSES


def test_applicant_ids_are_uppercase_keys():
    assert all(key == key.upper() for key in APPLICANTS)
