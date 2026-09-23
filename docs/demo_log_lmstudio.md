# Demo Log: Student Enrollment Assistant Agent

- **Model:** `qwen_qwen3.5-4b`
- **Endpoint:** `http://localhost:1234/v1`
- **Run at:** 2026-09-23 18:46
- **Session:** one session, 5 turns

## Turn 1

**User:**

> Hi, what programs do you offer in computer science?

**Tool calls:**

1. `get_program_info` with `{"program_name": "computer science"}`

   ```json
   {
     "matches": [
       {
         "program_name": "B.S. Computer Science",
         "duration": "4 years",
         "tuition": "$38,000 / year",
         "prerequisites": [
           "High school diploma",
           "Math through Pre-Calculus",
           "SAT/ACT optional"
         ]
       },
       {
         "program_name": "M.S. Computer Science",
         "duration": "2 years",
         "tuition": "$45,000 / year",
         "prerequisites": [
           "Bachelor's degree in Computer Science or a related field",
           "Coursework in Data Structures & Algorithms",
           "Minimum GPA of 3.0"
         ]
       }
     ]
   }
   ```

**Agent:**

> Here are the Computer Science programs we offer:
>
> **B.S. Computer Science**
> - Duration: 4 years
> - Tuition: $38,000 / year
> - Prerequisites: High school diploma, Math through Pre-Calculus, SAT/ACT optional
>
> **M.S. Computer Science**
> - Duration: 2 years
> - Tuition: $45,000 / year
> - Prerequisites: Bachelor's degree in Computer Science or related field, Coursework in Data Structures & Algorithms, Minimum GPA of 3.0
>
> Would you like to know more about either program or check deadlines?

_11.1 s_

## Turn 2

**User:**

> What's the application deadline for that?

**Tool calls:**

1. `get_deadlines` with `{"program_name": "B.S. Computer Science"}`

   ```json
   {
     "program_name": "B.S. Computer Science",
     "application_deadline": "2027-01-15",
     "document_submission_deadline": "2027-02-01",
     "decision_notification_date": "2027-03-31"
   }
   ```

2. `get_deadlines` with `{"program_name": "M.S. Computer Science"}`

   ```json
   {
     "program_name": "M.S. Computer Science",
     "application_deadline": "2027-02-01",
     "document_submission_deadline": "2027-02-15",
     "decision_notification_date": "2027-04-15"
   }
   ```

**Agent:**

> Here are the deadlines for each Computer Science program:
>
> **B.S. Computer Science:**
> - Application deadline: January 15, 2027
> - Document submission deadline: February 1, 2027
> - Decision notification date: March 31, 2027
>
> **M.S. Computer Science:**
> - Application deadline: February 1, 2027
> - Document submission deadline: February 15, 2027
> - Decision notification date: April 15, 2027
>
> Would you like to know about any other programs or check your application status?

_12.4 s_

## Turn 3

**User:**

> I already applied. My ID is APP-1042. What's my status?

**Tool calls:**

1. `check_application_status` with `{"applicant_id": "APP-1042"}`

   ```json
   {
     "applicant_id": "APP-1042",
     "applicant_name": "Jordan Lee",
     "program": "M.S. Computer Science",
     "status": "Documents Pending",
     "next_step": "Submit missing documents by 2027-02-15",
     "missing_documents": [
       "Official transcripts",
       "Two letters of recommendation"
     ]
   }
   ```

**Agent:**

> Here's your application status:
>
> **Applicant:** Jordan Lee (APP-1042)
> **Program Applied To:** M.S. Computer Science
> **Status:** Documents Pending
>
> **Next Steps:** Submit missing documents by February 15, 2027
>
> **Missing Documents Required:**
> - Official transcripts
> - Two letters of recommendation
>
> You need to submit these documents to complete your application. Would you like help with anything else?

_9.0 s_

## Turn 4

**User:**

> Can I get a fee waiver?

_No tool calls._

**Agent:**

> I'd recommend speaking with an enrollment counselor for that. Would you like me to connect you?

_6.2 s_

## Turn 5

**User:**

> What documents do I still need to submit?

_No tool calls._

**Agent:**

> Based on your application status for M.S. Computer Science (APP-1042), you still need to submit these documents:
>
> **Missing Documents:**
> - Official transcripts
> - Two letters of recommendation
>
> You need to submit these by February 15, 2027 to complete your application.

_4.6 s_
