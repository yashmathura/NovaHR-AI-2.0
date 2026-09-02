from agent.nlp.normalizer import normalize_query
from agent.nlp.entity_extractor import extract_entities
from agent.rag.service import answer_context
from agent.analytics.insights import narrative


ANALYTIC_PATTERNS = {
    "attendance_analytics": (
        "attendance analytics",
        "attendance trend",
        "attendance summary",
        "analyze attendance",
        "analyse attendance",
        "attendance report",
    ),
    "payroll_analytics": (
        "payroll trend",
        "salary trend",
        "payroll analytics",
        "payroll summary",
        "salary analytics",
        "analyze payroll",
        "analyse payroll",
        "show payroll trends",
    ),
    "workforce_analytics": (
        "workforce analytics",
        "employee analytics",
        "workforce summary",
        "employee summary",
    ),
}


def get_query_entities(message, normalized=None):
    message = message or ""

    try:
        entities = extract_entities(message) or {}
    except Exception:
        entities = {}

    if not (
        entities.get("employee_name")
        or entities.get("employee_id")
    ) and normalized:
        try:
            normalized_entities = extract_entities(normalized) or {}

            for key, value in normalized_entities.items():
                if value and not entities.get(key):
                    entities[key] = value
        except Exception:
            pass

    return entities


def has_employee_reference(entities):
    return bool(
        entities.get("employee_name")
        or entities.get("employee_id")
    )


def is_my_query(text):
    text = f" {str(text or '').lower().strip()} "

    self_words = (
        " my ",
        " myself ",
        " mine ",
        " mera ",
        " meri ",
        " mere ",
        " mujhe ",
        " meraa ",
    )

    return any(word in text for word in self_words)


def contains_policy_question(text):
    policy_phrases = (
        "what is",
        "what are",
        "explain",
        "tell me about",
        "policy",
        "rule",
        "what happens",
        "can i",
        "am i allowed",
        "allowed",
        "approval",
        "without approval",
        "how does",
        "how many",
    )

    return any(phrase in text for phrase in policy_phrases)


def contains_policy_topic(text):
    policy_topics = (
        "leave",
        "attendance",
        "payroll",
        "salary",
        "company",
        "policy",
        "approval",
        "working hours",
        "check in",
        "check out",
        "miss punch",
        "office timing",
        "holiday",
    )

    return any(topic in text for topic in policy_topics)


def is_global_analytics_request(text):
    analytics_words = (
        "analytics",
        "analyze",
        "analyse",
        "trend",
        "summary",
        "insight",
        "overview",
        "statistics",
        "stats",
    )

    return any(word in text for word in analytics_words)


def is_salary_change_query(text):
    phrases = (
        "why is my salary",
        "why did my salary",
        "why has my salary",
        "salary decreased",
        "salary decrease",
        "salary reduced",
        "salary reduction",
        "salary changed",
        "salary difference",
        "explain my salary",
        "why is my payroll",
        "why did my payroll",
        "payroll changed",
    )

    return any(phrase in text for phrase in phrases)


def is_direct_command(text):
    command_patterns = (
        # Employee management commands must bypass employee analytics.
        "add employee",
        "create employee",
        "onboard employee",
        "hire employee",
        "register employee",
        "new employee",
        "remove employee",
        "delete employee",
        "deactivate employee",
        "terminate employee",
        "update employee",
        "edit employee",
        "change employee",

        # Task commands.
        "assign task",
        "create task",
        "update task",
        "complete task",
        "finish task",
        "mark task",

        # Payroll commands.
        "generate payroll",
        "process payroll",
        "run payroll",
        "show payroll report",
        "payroll report",

        # Attendance commands.
        "show team attendance",
        "team attendance",
        "department attendance",

        # Leave commands.
        "show pending leaves",
        "list pending leaves",
        "approve leave",
        "reject leave",
        "apply leave",
        "cancel leave",

        # Attendance actions.
        "check in",
        "check out",
        "mark attendance",

        # Employee listing.
        "show all employees",
        "list employees",
    )

    return any(
        pattern in text
        for pattern in command_patterns
    )

def classify_advanced(message):
    message = message or ""

    normalized = normalize_query(message) or ""
    t = normalized.lower().strip()

    if not t:
        return None

    if is_direct_command(t):
        return None

    entities = get_query_entities(message, normalized)

    if (
        (
            "low attendance" in t
            or "attendance problem" in t
            or "poor attendance" in t
        )
        and (
            "task" in t
            or "tasks" in t
            or "pending" in t
        )
    ):
        return "multi_step_low_attendance_tasks"

    low_attendance_phrases = (
        "low attendance",
        "employees with low attendance",
        "employee with low attendance",
        "poor attendance",
        "attendance below",
        "who has low attendance",
        "who has the lowest attendance",
        "lowest attendance",
        "find low attendance employees",
    )

    if any(phrase in t for phrase in low_attendance_phrases):
        return "low_attendance_employees"

    if is_salary_change_query(t):
        return "explain_salary_change"

    if (
        "leave balance" in t
        or (
            is_my_query(t)
            and "leave" in t
            and "balance" in t
        )
    ):
        return "get_leave_balance"

    if (
        "attendance" in t
        and has_employee_reference(entities)
        and not is_my_query(t)
        and not is_global_analytics_request(t)
    ):
        return "employee_attendance"

    if (
        (
            "salary" in t
            or "payroll" in t
            or "pay" in t
        )
        and has_employee_reference(entities)
        and not is_my_query(t)
        and not is_global_analytics_request(t)
    ):
        return "employee_payroll"

    if (
        (
            "task" in t
            or "tasks" in t
            or "todo" in t
            or "to-do" in t
            or "work" in t
        )
        and has_employee_reference(entities)
        and not is_my_query(t)
        and not is_global_analytics_request(t)
    ):
        return "employee_tasks"

    if (
        "leave" in t
        and has_employee_reference(entities)
        and not is_my_query(t)
        and not contains_policy_question(t)
    ):
        return "employee_leave"

    if (
        "attendance" in t
        and is_my_query(t)
        and not is_global_analytics_request(t)
    ):
        return "my_attendance"

    if (
        (
            "salary" in t
            or "payroll" in t
        )
        and is_my_query(t)
        and not is_global_analytics_request(t)
    ):
        return "my_payroll"

    if any(
        phrase in t
        for phrase in ANALYTIC_PATTERNS["payroll_analytics"]
    ):
        return "payroll_analytics"

    if any(
        phrase in t
        for phrase in ANALYTIC_PATTERNS["attendance_analytics"]
    ):
        return "attendance_analytics"

    if (
        is_global_analytics_request(t)
        and any(
            word in t
            for word in (
                "attendance",
                "present",
                "absent",
                "late",
                "miss punch",
            )
        )
    ):
        return "attendance_analytics"

    if any(
        phrase in t
        for phrase in ANALYTIC_PATTERNS["workforce_analytics"]
    ):
        return "workforce_analytics"

    if (
        contains_policy_question(t)
        and contains_policy_topic(t)
        and not has_employee_reference(entities)
    ):
        return "rag_policy"

    return None


def enrich(message, result):
    result = result or {}

    normalized = normalize_query(message) or ""

    entities = get_query_entities(
        message,
        normalized,
    )

    extra = {
        "normalized_query": normalized,
        "entities": entities,
    }

    intent = result.get("intent")

    if intent in (
        "get_policy",
        "rag_policy",
    ):
        try:
            extra["sources"] = answer_context(message)
        except Exception:
            extra["sources"] = []

    if result.get("analytics"):
        try:
            extra["insight"] = narrative(
                result["analytics"]
            )
        except Exception:
            extra["insight"] = (
                "Analytics completed successfully."
            )

    result.update(extra)

    return result