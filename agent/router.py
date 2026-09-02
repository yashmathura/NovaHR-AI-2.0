import re

from datetime import date, timedelta

from agent.novalm import predict_intent
from agent.nlp_engine import classify


INTENTS = {
    "create_employee": [
        r"\b(add|create|onboard|hire|register)\b.*\b(employee|staff)\b",
        r"\bnew\s+employee\b",
    ],
    "delete_employee": [
        r"\b(remove|delete|deactivate|terminate)\b.*\b(employee|staff)\b",
    ],
    "update_employee": [
        r"\b(update|edit|change)\b.*\b(employee|staff|profile)\b",
    ],
    "assign_task": [
        r"\bassign\b.*\b(task|work)\b",
        r"\bcreate\b.*\b(task|work)\b",
    ],
    "update_task": [
        r"\b(update|complete|finish|change)\b.*\b(task|work)\b",
        r"\bmark\b.*\btask\b.*\bdone\b",
        r"\btask\s+\d+\s+done\b",
    ],
    "generate_payroll": [
        r"\b(generate|process|run)\b.*\b(payroll|payslip)\b",
    ],
    "get_payroll_report": [
        r"\b(payroll|salary)\b.*\b(report|summary|total|department)\b",
        r"\bpayroll\b.*\bteam\b",
        r"\bshow\s+payroll\s+report\b",
    ],
    "approve_leave": [
        r"\b(approve|accept)\b.*\bleave\b",
    ],
    "reject_leave": [
        r"\b(reject|deny)\b.*\bleave\b",
    ],
    "apply_leave": [
        r"\b(apply|request|take)\b.*\b(leave|vacation|time\s+off)\b",
        r"\bneed\b.*\bleave\b",
    ],
    "cancel_leave": [
        r"\b(cancel|withdraw)\b.*\bleave\b",
    ],
    "mark_attendance": [
        r"\b(mark|check|punch|log)\b.*\b(attendance|in)\b",
        r"\bcheck[-\s]?in\s+today\b",
        r"\bcheck[-\s]?in\b",
    ],
    "check_out": [
        r"\bcheck[-\s]?out\b",
        r"\bpunch\s+out\b",
        r"\blog\s+out\b",
    ],
    "get_team_attendance": [
        r"\b(team|department)\b.*\b(attendance|absent|present)\b",
        r"\bwho\b.*\b(absent|present)\b.*\btoday\b",
        r"\bshow\s+team\s+attendance\b",
    ],
    "get_leave_balance": [
        r"\b(leaves?|vacation|time\s+off)\b.*\b(balance|left|remaining|available)\b",
        r"\bhow\s+many\s+(leaves?|days)\b",
        r"\bleave\s+balance\b",
    ],
    "get_payroll": [
        r"\b(salary|payroll|payslip|pay)\b",
        r"\bearning\b",
        r"\bsalary\s+revision\b",
        r"\bsalary\s+lower\b",
    ],
    "get_attendance": [
        r"\battendance\b",
        r"\battendace\b",
        r"\battendence\b",
        r"\bhow\s+many\s+days\b.*\bpresent\b",
        r"\bam\s+i\s+absent\b",
    ],
    "get_tasks": [
        r"\b(task|tasks|todo|to-do|work)\b",
        r"\bassigned\s+work\b",
        r"\bpending\s+tasks?\b",
    ],
    "get_policy": [
        r"\b(policy|policies|rule|rules)\b",
        r"\bcompany\s+policy\b",
        r"\bworking\s+hours?\b",
        r"\bwork\s+hours?\b",
        r"\bmiss\s+(a\s+)?punch\b",
        r"\bmissing\s+punch\b",
        r"\bleave\s+without\s+approval\b",
    ],
    "analyze_performance": [
        r"\bperformance\b",
        r"\bperformance\s+score\b",
    ],
    "team_performance": [
        r"\b(team|department)\b.*\bperformance\b",
    ],
    "list_employees": [
        r"\b(list|show|find|search)\b.*\b(employee|employees|staff|people)\b",
        r"\bwho\s+works\b",
        r"\bshow\s+all\s+employees\b",
    ],
    "get_employee": [
        r"\b(employee|staff)\b.*\b(profile|details|info|information)\b",
    ],
    "send_notification": [
        r"\b(send|notify|message)\b.*\b(notification|employee|staff)\b",
    ],
    "get_notifications": [
        r"\b(notification|notifications|alerts?)\b",
    ],
    "mark_notifications_read": [
        r"\b(mark|clear)\b.*\b(notification|notifications)\b.*\bread\b",
    ],
    "profile": [
        r"\bmy\s+profile\b",
        r"\bmy\s+details\b",
        r"\bmy\s+information\b",
        r"\bwho\s+am\s+i\b",
    ],
    "list_pending_leaves": [
        r"\b(show|get|list|view)\b.*\bpending\s+leaves?\b",
        r"\bpending\s+leave\s+(requests?|applications?)\b",
    ],
    "department_summary": [
        r"\b(department|team)\b.*\b(summary|overview|workload)\b",
    ],
}


def resolve_intent(text):
    t = (text or "").lower().strip()

    if not t:
        return "UNKNOWN"

    priority_rules = (
        (
            "create_employee",
            (
                r"\b(add|create|onboard|hire|register)\b.*\b(employee|staff)\b",
                r"\bnew\s+employee\b",
            ),
        ),
        (
            "delete_employee",
            (
                r"\b(remove|delete|deactivate|terminate)\b.*\b(employee|staff)\b",
            ),
        ),
        (
            "update_employee",
            (
                r"\b(update|edit|change)\b.*\b(employee|staff)\b",
            ),
        ),
        (
            "generate_payroll",
            (
                r"\b(generate|process|run)\b.*\b(payroll|payslip)\b",
            ),
        ),
        (
            "get_payroll_report",
            (
                r"\b(show|get|view)?\s*payroll\s+(report|summary)\b",
                r"\bpayroll\s+report\b",
            ),
        ),
        (
            "approve_leave",
            (
                r"\b(approve|accept)\b.*\bleave\b",
            ),
        ),
        (
            "reject_leave",
            (
                r"\b(reject|deny)\b.*\bleave\b",
            ),
        ),
        (
            "cancel_leave",
            (
                r"\b(cancel|withdraw)\b.*\bleave\b",
            ),
        ),
        (
            "apply_leave",
            (
                r"\b(apply|request|take)\b.*\b(leave|vacation|time\s+off)\b",
                r"\bneed\b.*\bleave\b",
            ),
        ),
        (
            "assign_task",
            (
                r"\bassign\b.*\b(task|work)\b",
            ),
        ),
        (
            "update_task",
            (
                r"\btask\s+\d+\s+(done|complete|completed|finished)\b",
                r"\bmark\b.*\btask\b.*\bdone\b",
            ),
        ),
        (
            "check_out",
            (
                r"\bcheck[-\s]?out\b",
                r"\bpunch\s+out\b",
            ),
        ),
        (
            "mark_attendance",
            (
                r"\bcheck[-\s]?in\b",
                r"\bmark\s+attendance\b",
                r"\bpunch\s+in\b",
            ),
        ),
        (
            "get_team_attendance",
            (
                r"\b(team|department)\s+attendance\b",
                r"\bshow\s+team\s+attendance\b",
            ),
        ),
        (
            "list_pending_leaves",
            (
                r"\b(show|get|list|view)\b.*\bpending\s+leaves?\b",
                r"\bpending\s+leave\s+(requests?|applications?)\b",
            ),
        ),
        (
            "get_leave_balance",
            (
                r"\bleave\s+balance\b",
                r"\b(leaves?|vacation|time\s+off)\b.*\b(balance|left|remaining|available)\b",
            ),
        ),
        (
            "explain_salary_change",
            (
                r"\bwhy\b.*\b(salary|payroll)\b.*\b(change|changed|decrease|decreased|lower|reduced)\b",
                r"\bwhy\s+did\b.*\bsalary\s+change\b",
            ),
        ),
        (
            "get_policy",
            (
                r"\b(working|work)\s+hours?\b",
                r"\bmiss(?:ing)?\s+(?:a\s+)?punch\b",
                r"\bleave\s+without\s+approval\b",
                r"\b(policy|policies|rules?)\b",
            ),
        ),
        (
            "profile",
            (
                r"\b(my\s+profile|my\s+details|who\s+am\s+i)\b",
            ),
        ),
    )

    for intent, patterns in priority_rules:
        if any(
            re.search(pattern, t, re.IGNORECASE)
            for pattern in patterns
        ):
            return intent

    try:
        nlp_result = classify(t) or {}
        nlp_intent = nlp_result.get("intent")
        nlp_confidence = float(
            nlp_result.get("confidence", 0) or 0
        )

        if (
            nlp_intent in INTENTS
            and nlp_confidence >= 0.70
        ):
            return nlp_intent

    except Exception:
        pass

    try:
        learned = predict_intent(t) or {}
        learned_intent = learned.get("intent")
        learned_confidence = float(
            learned.get("confidence", 0) or 0
        )

        if (
            learned_intent in INTENTS
            and learned_confidence >= 0.75
        ):
            return learned_intent

    except Exception:
        pass

    for intent, patterns in INTENTS.items():
        for pattern in patterns:
            try:
                if re.search(
                    pattern,
                    t,
                    re.IGNORECASE,
                ):
                    return intent
            except re.error:
                continue

    return "UNKNOWN"


def extract_employee_id(text):
    match = re.search(
        r"\bE\d{3,}\b",
        text or "",
        re.IGNORECASE,
    )

    return (
        match.group(0).upper()
        if match
        else None
    )


def extract_leave_type(text, default=None):
    """
    Returns the explicitly requested leave type.

    IMPORTANT:
    For queries like 'leave balance', returning CASUAL as a
    default would incorrectly hide Sick and Annual balances.
    """

    t = (text or "").upper()

    aliases = {
        "CASUAL": ("CASUAL", "CL"),
        "SICK": ("SICK", "MEDICAL", "SL"),
        "ANNUAL": (
            "ANNUAL",
            "VACATION",
            "EARNED",
            "AL",
        ),
    }

    for leave_type, values in aliases.items():
        if any(
            re.search(
                rf"\b{re.escape(value)}\b",
                t,
            )
            for value in values
        ):
            return leave_type

    return default


def extract_status(text):
    t = (text or "").upper()

    patterns = {
        "DONE": [
            r"\bDONE\b",
            r"\bCOMPLETE(?:D)?\b",
            r"\bFINISH(?:ED)?\b",
        ],
        "IN_PROGRESS": [
            r"\bIN_PROGRESS\b",
            r"\bIN\s+PROGRESS\b",
            r"\bSTARTED\b",
        ],
        "TODO": [
            r"\bTODO\b",
            r"\bTO[-\s]?DO\b",
            r"\bPENDING\b",
        ],
    }

    for status, values in patterns.items():
        for pattern in values:
            if re.search(pattern, t):
                return status

    return None


def extract_priority(text):
    t = (text or "").upper()

    if re.search(
        r"\b(URGENT|CRITICAL)\b",
        t,
    ):
        return "HIGH"

    if re.search(r"\bHIGH\b", t):
        return "HIGH"

    if re.search(r"\bLOW\b", t):
        return "LOW"

    return "MEDIUM"


def extract_dates(text):
    t = (text or "").lower()
    today = date.today()

    if "day after tomorrow" in t:
        target = today + timedelta(days=2)
        return target, target

    if "tomorrow" in t:
        target = today + timedelta(days=1)
        return target, target

    if "today" in t:
        return today, today

    matches = re.findall(
        r"\b\d{4}-\d{2}-\d{2}\b",
        t,
    )

    if not matches:
        return None, None

    try:
        start_date = date.fromisoformat(
            matches[0]
        )

        end_date = (
            date.fromisoformat(matches[1])
            if len(matches) > 1
            else start_date
        )

        return start_date, end_date

    except ValueError:
        return None, None


def extract_kv(text):
    pairs = {}

    keys = (
        "name",
        "email",
        "phone",
        "job_title",
        "employee_id",
        "department",
        "salary",
        "title",
        "description",
        "due_date",
        "message",
        "reason",
        "role",
        "password",
    )

    source = text or ""

    for key in keys:
        match = re.search(
            rf"\b{re.escape(key)}\s*[:=]\s*([^,;\n]+)",
            source,
            re.IGNORECASE,
        )

        if match:
            pairs[key] = match.group(1).strip()

    return pairs