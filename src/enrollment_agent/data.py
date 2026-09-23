"""Hardcoded mock data for programs, deadlines and applicants (FR-4, design §4)."""

VALID_STATUSES = ("Under Review", "Accepted", "Documents Pending", "Rejected")

PROGRAMS: dict[str, dict] = {
    "bs-cs": {
        "program_name": "B.S. Computer Science",
        "duration": "4 years",
        "tuition": "$38,000 / year",
        "prerequisites": [
            "High school diploma",
            "Math through Pre-Calculus",
            "SAT/ACT optional",
        ],
        "aliases": [
            "cs",
            "bscs",
            "bs cs",
            "bachelors computer science",
            "bachelor of science in computer science",
            "undergraduate computer science",
        ],
    },
    "ms-cs": {
        "program_name": "M.S. Computer Science",
        "duration": "2 years",
        "tuition": "$45,000 / year",
        "prerequisites": [
            "Bachelor's degree in Computer Science or a related field",
            "Coursework in Data Structures & Algorithms",
            "Minimum GPA of 3.0",
        ],
        "aliases": [
            "cs",
            "mscs",
            "ms cs",
            "masters computer science",
            "master of science in computer science",
            "graduate computer science",
        ],
    },
    "mba": {
        "program_name": "Master of Business Administration",
        "duration": "2 years",
        "tuition": "$52,000 / year",
        "prerequisites": [
            "Bachelor's degree in any field",
            "2+ years of work experience",
            "GMAT or GRE score",
        ],
        "aliases": ["mba", "business administration"],
    },
    "bs-me": {
        "program_name": "B.S. Mechanical Engineering",
        "duration": "4 years",
        "tuition": "$40,000 / year",
        "prerequisites": [
            "High school diploma",
            "Physics",
            "Calculus",
        ],
        "aliases": ["bsme", "mechanical engineering"],
    },
}

DEADLINES: dict[str, dict] = {
    "bs-cs": {
        "application_deadline": "2027-01-15",
        "document_submission_deadline": "2027-02-01",
        "decision_notification_date": "2027-03-31",
    },
    "ms-cs": {
        "application_deadline": "2027-02-01",
        "document_submission_deadline": "2027-02-15",
        "decision_notification_date": "2027-04-15",
    },
    "mba": {
        "application_deadline": "2027-03-01",
        "document_submission_deadline": "2027-03-15",
        "decision_notification_date": "2027-05-01",
    },
    "bs-me": {
        "application_deadline": "2027-01-15",
        "document_submission_deadline": "2027-02-01",
        "decision_notification_date": "2027-03-31",
    },
}

APPLICANTS: dict[str, dict] = {
    "APP-1042": {
        "applicant_name": "Jordan Lee",
        "program_id": "ms-cs",
        "status": "Documents Pending",
        "next_step": "Submit missing documents by 2027-02-15",
        "missing_documents": ["Official transcripts", "Two letters of recommendation"],
    },
    "APP-1043": {
        "applicant_name": "Priya Sharma",
        "program_id": "bs-cs",
        "status": "Under Review",
        "next_step": "Await decision by 2027-03-31",
        "missing_documents": [],
    },
    "APP-1044": {
        "applicant_name": "Marcus Chen",
        "program_id": "mba",
        "status": "Accepted",
        "next_step": "Pay enrollment deposit by 2027-05-15",
        "missing_documents": [],
    },
    "APP-1045": {
        "applicant_name": "Aisha Okafor",
        "program_id": "bs-me",
        "status": "Rejected",
        "next_step": "Contact admissions for feedback",
        "missing_documents": [],
    },
}
