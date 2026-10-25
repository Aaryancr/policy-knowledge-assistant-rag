"""Synthetic policy documents and benchmark test questions for RAG evaluation."""

from dataclasses import dataclass
from typing import Any

# 1. Four Synthetic Enterprise Policy Documents
SAMPLE_DOCUMENTS: dict[str, dict[str, Any]] = {
    "remote_work_policy": {
        "title": "Remote Work and Flexibility Policy",
        "filename": "remote_work_policy.txt",
        "content_type": "text/plain",
        "content": """# Remote Work and Flexibility Policy

## Eligibility
All full-time employees who have successfully completed their 90-day probationary period are eligible to request hybrid or full remote work arrangements. Approval must be granted in writing by both the employee's direct manager and the department VP. Performance evaluations must consistently reflect satisfactory or exceeding expectations ratings. Contractors and temporary interns are not eligible for permanent remote work status unless explicitly approved by Human Resources.

## Core Working Hours
All remote team members must be online and available on Slack and email during core collaboration hours: 10:00 AM to 4:00 PM Eastern Standard Time (EST), regardless of local time zone. Flexibility outside core hours is permitted for asynchronous tasks, but cross-team standups and sprint planning sessions scheduled during core hours are mandatory. Employees must update their calendar status to reflect their working window and timezone.

## Equipment Stipend
Eligible remote employees receive a one-time home office equipment stipend of $500 upon starting a designated remote arrangement. Reimbursable items include external monitors, ergonomic chairs, keyboards, and mice. All receipts must be submitted within 60 days of purchase through the procurement portal. Company-issued laptops remain corporate property, while peripheral accessories purchased using the equipment stipend belong to the employee after 12 months of tenure. Equipment refresh cycles occur every 3 years.

## Security Protocols
Remote workers must connect to the corporate Virtual Private Network (VPN) whenever accessing internal company resources. Connecting to company systems over unsecured public Wi-Fi without VPN activation is strictly forbidden. Hard drives on all remote devices must have full disk encryption enabled via corporate endpoint policy. Family members or unauthorized third parties are strictly prohibited from using company-issued devices for any personal purpose.

## Workspace Safety and Reporting
Remote employees must maintain a dedicated, distraction-free, and ergonomically sound workspace. Any work-related injury occurring during established working hours within the designated home workspace must be reported to People Operations within 24 hours to initiate worker compensation claims.
""",
    },
    "leave_and_time_off_policy": {
        "title": "Leave and Paid Time Off Policy",
        "filename": "leave_and_time_off_policy.txt",
        "content_type": "text/plain",
        "content": """# Leave and Paid Time Off Policy

## Annual Paid Time Off (PTO)
Full-time employees accrue 20 days of paid time off per calendar year, accrued at a rate of 1.67 days per month. Part-time employees accrue PTO on a pro-rata basis. PTO requests exceeding 3 consecutive days must be submitted at least 2 weeks in advance through the HR management system. Managers must approve or provide feedback on PTO requests within 3 business days of submission. PTO accrual begins on the employee's official start date.

## PTO Carryover
A maximum of 5 unused PTO days may be carried over into the following calendar year. Any carried-over days must be utilized before March 31 of that year, or they will expire and be forfeited without cash payout. Employees may not exchange accrued or carried-over PTO for cash compensation during employment, except where explicitly mandated by state labor legislation.

## Sick Leave
Employees receive 10 paid sick days annually, available starting on the first day of employment without waiting for probationary periods to conclude. Sick leave covers employee illness, preventive medical appointments, and caring for an immediate family member. For any consecutive sick leave absence exceeding 3 days, a written medical note from a licensed healthcare provider is mandatory before resuming work. Unused sick leave does not roll over to the following calendar year and is non-compensable upon separation.

## Bereavement Leave
Employees are entitled to up to 3 consecutive business days of fully paid bereavement leave for immediate family members (spouse, child, parent, sibling). For extended family members (grandparent, aunt, uncle), 1 day of paid bereavement leave is provided. Additional unpaid bereavement leave of up to 5 business days may be requested with direct manager approval. Documentation such as an obituary or funeral announcement may be requested by HR.

## Parental and Family Leave
Eligible employees welcoming a new child through birth, adoption, or foster placement are entitled to 12 weeks of fully paid parental leave, to be taken within the first 12 months of the qualifying event. Parental leave runs concurrently with statutory family leave allowances where applicable.
""",
    },
    "it_security_and_device_policy": {
        "title": "IT Security and Device Usage Policy",
        "filename": "it_security_and_device_policy.txt",
        "content_type": "text/plain",
        "content": """# IT Security and Device Usage Policy

## Password Complexity and Rotation
Passwords for all corporate accounts must contain a minimum of 14 characters, including at least one uppercase letter, one lowercase letter, one number, and one special symbol. Passwords must be changed every 90 days. Reusing any of the previous 5 passwords is prohibited. Multi-factor authentication (MFA) via authenticator app or hardware security key is required for all single sign-on corporate tools and cannot be bypassed.

## Device Lock and Clean Desk
All company-issued laptops must be locked immediately whenever left unattended. The automatic screen timeout lock is set to 5 minutes of inactivity and cannot be modified by employees. Printed documents containing confidential information must be locked away in secure filing cabinets at the end of each workday. Laptops left in personal vehicles must be stored out of sight in the locked trunk.

## Security Incident Reporting
Any suspected security breach, phishing email, lost laptop, or malware detection must be reported immediately to security@company.com within 1 hour of discovery. Failure to report security incidents may result in disciplinary action up to termination. The internal cybersecurity incident response team will isolate compromised devices remotely within 30 minutes of notification.

## Removable Media Restrictions
External USB flash drives and unauthorized portable storage devices are disabled by endpoint management software. Data transfers to unauthorized external drives are blocked to prevent data exfiltration. Approved encrypted cloud storage (corporate Google Drive and SharePoint) must be utilized for all shared team deliverables and backups.

## Software Installation and Admin Rights
Employees may not install unapproved software, peer-to-peer applications, or browser extensions on company-issued workstations. All software additions must be requested through IT Service Desk tickets and evaluated for enterprise vulnerability compliance. Local administrative privileges are restricted to authorized IT operations personnel.
""",
    },
    "travel_and_expense_policy": {
        "title": "Corporate Travel and Expense Policy",
        "filename": "travel_and_expense_policy.txt",
        "content_type": "text/plain",
        "content": """# Corporate Travel and Expense Policy

## Per Diem Rates
Employees traveling on business receive a meal per diem allowance of $75 per day for domestic travel within the United States, and $100 per day for international travel. Alcohol purchases are non-reimbursable under standard per diem rules. For partial travel days where travel begins after 12:00 PM or concludes before 12:00 PM, per diem allowances are prorated at 50 percent of the standard rate.

## Flight Class Guidelines
All domestic flights must be booked in economy class. Business class travel is permitted only for international flights with a continuous scheduled flight duration exceeding 8 hours, subject to pre-approval by the CFO. Flight reservations must be booked at least 14 days in advance through the designated corporate travel platform to take advantage of negotiated enterprise rates.

## Receipt Requirements and Expense Submission
Itemized receipts are required for all business expenses of $25 or greater. All expense reimbursement reports must be submitted via the expense portal within 30 days of the travel end date. Late submissions will not be reimbursed without exceptional VP-level sign-off. Credit card statements alone do not qualify as itemized proof of purchase.

## Lodging and Ground Transportation
Hotel accommodations must be booked at standard single-occupancy rates not exceeding $250 per night in primary metropolitan areas or $175 per night in secondary cities. Rideshare services (Uber, Lyft) or public transit are preferred over rental cars unless public transportation is unavailable or economically unviable. Personal vehicle usage for business travel is reimbursed at the prevailing federal IRS mileage standard.
""",
    },
}


# 2. Benchmark Evaluation Test Suite (28 Questions)
@dataclass
class EvalQuestion:
    id: str
    question: str
    expected_doc: str | None  # None if unanswerable
    expected_section: str | None
    is_answerable: bool
    expected_facts: list[str]  # Key phrases expected in correct answer
    question_type: str  # "direct", "cross_section", "distractor", "unanswerable"


EVAL_QUESTIONS: list[EvalQuestion] = [
    # Direct Answerable Questions
    EvalQuestion(
        id="Q01",
        question="What is the minimum password length required for corporate accounts?",
        expected_doc="it_security_and_device_policy",
        expected_section="Password Complexity and Rotation",
        is_answerable=True,
        expected_facts=["14", "character"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q02",
        question="How many days of paid time off do full-time employees accrue per year?",
        expected_doc="leave_and_time_off_policy",
        expected_section="Annual Paid Time Off (PTO)",
        is_answerable=True,
        expected_facts=["20 days", "pto"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q03",
        question="What is the one-time home office equipment stipend for remote workers?",
        expected_doc="remote_work_policy",
        expected_section="Equipment Stipend",
        is_answerable=True,
        expected_facts=["$500", "stipend"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q04",
        question="What are the core collaboration hours for remote team members?",
        expected_doc="remote_work_policy",
        expected_section="Core Working Hours",
        is_answerable=True,
        expected_facts=["10:00 am", "4:00 pm", "eastern"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q05",
        question="How much is the domestic daily meal per diem allowance?",
        expected_doc="travel_and_expense_policy",
        expected_section="Per Diem Rates",
        is_answerable=True,
        expected_facts=["$75", "per day"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q06",
        question="What is the international meal per diem allowance?",
        expected_doc="travel_and_expense_policy",
        expected_section="Per Diem Rates",
        is_answerable=True,
        expected_facts=["$100"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q07",
        question="When is business class air travel permitted?",
        expected_doc="travel_and_expense_policy",
        expected_section="Flight Class Guidelines",
        is_answerable=True,
        expected_facts=["international", "8 hours", "cfo"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q08",
        question="How many days of PTO can be carried over into the next year?",
        expected_doc="leave_and_time_off_policy",
        expected_section="PTO Carryover",
        is_answerable=True,
        expected_facts=["5", "march 31"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q09",
        question="When must carried-over PTO be utilized before expiring?",
        expected_doc="leave_and_time_off_policy",
        expected_section="PTO Carryover",
        is_answerable=True,
        expected_facts=["march 31"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q10",
        question="When is a doctor's note required for sick leave?",
        expected_doc="leave_and_time_off_policy",
        expected_section="Sick Leave",
        is_answerable=True,
        expected_facts=["3", "consecutive", "doctor", "medical"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q11",
        question="How many days of bereavement leave are granted for an immediate family member?",
        expected_doc="leave_and_time_off_policy",
        expected_section="Bereavement Leave",
        is_answerable=True,
        expected_facts=["3", "immediate family"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q12",
        question="How frequently must corporate passwords be changed?",
        expected_doc="it_security_and_device_policy",
        expected_section="Password Complexity and Rotation",
        is_answerable=True,
        expected_facts=["90 days"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q13",
        question="Within how many hours must a security incident or lost laptop be reported?",
        expected_doc="it_security_and_device_policy",
        expected_section="Security Incident Reporting",
        is_answerable=True,
        expected_facts=["1 hour", "security@company.com"],
        question_type="direct",
    ),
    EvalQuestion(
        id="Q14",
        question="What is the inactivity timeout for screen lock on company laptops?",
        expected_doc="it_security_and_device_policy",
        expected_section="Device Lock and Clean Desk",
        is_answerable=True,
        expected_facts=["5 minutes"],
        question_type="direct",
    ),

    # Cross-Section / Cross-Document Questions
    EvalQuestion(
        id="Q15",
        question="Who must approve a remote work arrangement, and what network protocol is required?",
        expected_doc="remote_work_policy",
        expected_section="Eligibility",
        is_answerable=True,
        expected_facts=["manager", "vp", "vpn"],
        question_type="cross_section",
    ),
    EvalQuestion(
        id="Q16",
        question="What receipts must be saved for travel expenses, and within what window must expense reports be submitted?",
        expected_doc="travel_and_expense_policy",
        expected_section="Receipt Requirements and Expense Submission",
        is_answerable=True,
        expected_facts=["$25", "30 days"],
        question_type="cross_section",
    ),
    EvalQuestion(
        id="Q17",
        question="Can an employee use USB flash drives to store company files, and what happens when leaving a laptop unattended?",
        expected_doc="it_security_and_device_policy",
        expected_section="Removable Media Restrictions",
        is_answerable=True,
        expected_facts=["disabled", "blocked", "locked"],
        question_type="cross_section",
    ),
    EvalQuestion(
        id="Q18",
        question="How much sick leave do employees get, and do they have to wait until probationary period ends?",
        expected_doc="leave_and_time_off_policy",
        expected_section="Sick Leave",
        is_answerable=True,
        expected_facts=["10", "first day"],
        question_type="cross_section",
    ),
    EvalQuestion(
        id="Q19",
        question="How many days notice must be provided when requesting PTO longer than 3 days?",
        expected_doc="leave_and_time_off_policy",
        expected_section="Annual Paid Time Off (PTO)",
        is_answerable=True,
        expected_facts=["2 weeks"],
        question_type="cross_section",
    ),

    # Distractor / Confusing Questions
    EvalQuestion(
        id="Q20",
        question="Can an employee roll over 10 days of unused vacation to the next year?",
        expected_doc="leave_and_time_off_policy",
        expected_section="PTO Carryover",
        is_answerable=True,
        expected_facts=["maximum of 5", "5 days"],
        question_type="distractor",
    ),
    EvalQuestion(
        id="Q21",
        question="Can alcohol be reimbursed under standard travel per diem allowances?",
        expected_doc="travel_and_expense_policy",
        expected_section="Per Diem Rates",
        is_answerable=True,
        expected_facts=["alcohol", "non-reimbursable"],
        question_type="distractor",
    ),
    EvalQuestion(
        id="Q22",
        question="Can remote employees connect to public Wi-Fi in coffee shops?",
        expected_doc="remote_work_policy",
        expected_section="Security Protocols",
        is_answerable=True,
        expected_facts=["vpn", "forbidden"],
        question_type="distractor",
    ),
    EvalQuestion(
        id="Q23",
        question="Can a newly hired employee work remotely during their first 30 days?",
        expected_doc="remote_work_policy",
        expected_section="Eligibility",
        is_answerable=True,
        expected_facts=["90-day", "probationary"],
        question_type="distractor",
    ),

    # Explicitly Unanswerable Questions (Abstention Required)
    EvalQuestion(
        id="Q24",
        question="What is the company subsidy for pet insurance?",
        expected_doc=None,
        expected_section=None,
        is_answerable=False,
        expected_facts=[],
        question_type="unanswerable",
    ),
    EvalQuestion(
        id="Q25",
        question="Can employees bring dogs or emotional support animals into the physical office?",
        expected_doc=None,
        expected_section=None,
        is_answerable=False,
        expected_facts=[],
        question_type="unanswerable",
    ),
    EvalQuestion(
        id="Q26",
        question="How much is the annual year-end performance bonus percentage?",
        expected_doc=None,
        expected_section=None,
        is_answerable=False,
        expected_facts=[],
        question_type="unanswerable",
    ),
    EvalQuestion(
        id="Q27",
        question="What is the monthly gym and fitness reimbursement stipend?",
        expected_doc=None,
        expected_section=None,
        is_answerable=False,
        expected_facts=[],
        question_type="unanswerable",
    ),
    EvalQuestion(
        id="Q28",
        question="Does the company offer a corporate vehicle lease program?",
        expected_doc=None,
        expected_section=None,
        is_answerable=False,
        expected_facts=[],
        question_type="unanswerable",
    ),
]
