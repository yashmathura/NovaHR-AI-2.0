import re
import math
from collections import Counter, defaultdict


INTENT_EXAMPLES = {
    "get_leave_balance": [
        "how many leaves do I have",
        "show my leave balance",
        "how much leave is left",
        "remaining leaves",
        "leave balance",
        "how many casual leaves are left",
        "how many sick leaves do I have",
        "annual leave remaining",
    ],
    "get_payroll": [
        "show my salary",
        "what is my salary",
        "show my payroll",
        "salary details",
        "pay slip",
        "payslip",
        "my salary this month",
        "why is my salary lower",
        "salary reduced",
        "salary deduction",
        "last salary revision",
        "when was my salary revised",
    ],
    "get_attendance": [
        "show my attendance",
        "my attendance",
        "attendance record",
        "attendance this month",
        "how many days was I present",
        "show attendance",
    ],
    "get_team_attendance": [
        "team attendance",
        "show employee attendance",
        "attendance of my team",
        "who is present today",
        "team present",
    ],
    "get_tasks": [
        "show my tasks",
        "pending tasks",
        "my pending tasks",
        "what tasks do I have",
        "show tasks",
        "assigned tasks",
    ],
    "assign_task": [
        "assign task",
        "give task to employee",
        "create task for",
        "assign work",
        "assign work to",
    ],
    "apply_leave": [
        "apply leave",
        "request leave",
        "take leave",
        "apply for sick leave",
        "apply casual leave",
        "need leave",
    ],
    "cancel_leave": [
        "cancel leave",
        "withdraw leave",
        "remove my leave",
    ],
    "approve_leave": [
        "approve leave",
        "accept leave",
        "approve leave request",
    ],
    "reject_leave": [
        "reject leave",
        "deny leave",
        "reject leave request",
    ],
    "list_employees": [
        "show employees",
        "list employees",
        "all employees",
        "employee list",
        "who works here",
    ],
    "get_employee": [
        "show employee",
        "employee details",
        "find employee",
        "details of employee",
        "information about employee",
    ],
    "create_employee": [
        "add employee",
        "create employee",
        "new employee",
        "hire employee",
        "register employee",
    ],
    "update_employee": [
        "update employee",
        "edit employee",
        "change employee details",
        "modify employee",
    ],
    "delete_employee": [
        "delete employee",
        "remove employee",
        "deactivate employee",
    ],
    "get_policy": [
        "company policy",
        "show policy",
        "leave policy",
        "hr policy",
        "what is the policy",
        "policy regarding",
    ],
    "analyze_performance": [
        "my performance",
        "performance report",
        "how am I performing",
        "performance score",
    ],
    "team_performance": [
        "team performance",
        "employee performance",
        "performance of my team",
    ],
    "get_notifications": [
        "show notifications",
        "my notifications",
        "unread notifications",
        "notifications",
    ],
    "mark_notifications_read": [
        "mark notifications read",
        "read notifications",
        "clear notifications",
    ],
    "profile": [
        "my profile",
        "show my details",
        "my employee details",
        "who am I",
    ],
    "department_summary": [
        "department summary",
        "department report",
        "department statistics",
    ],
    "mark_attendance": [
        "mark attendance",
        "check in",
        "checkin",
        "start attendance",
    ],
    "check_out": [
        "check out",
        "checkout",
        "mark checkout",
        "end attendance",
    ],
}


STOPWORDS = {
    "the", "a", "an", "is", "are", "am", "i", "my", "me",
    "to", "of", "for", "in", "on", "and", "or", "do",
    "does", "have", "has", "can", "you", "show", "please",
    "what", "when", "how", "much", "many", "this", "that"
}


def normalize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text):
    return [
        word for word in normalize(text).split()
        if word not in STOPWORDS and len(word) > 1
    ]


def similarity(text_a, text_b):
    a = tokenize(text_a)
    b = tokenize(text_b)

    if not a or not b:
        return 0.0

    ca = Counter(a)
    cb = Counter(b)

    common = set(ca) & set(cb)

    dot = sum(ca[x] * cb[x] for x in common)

    norm_a = math.sqrt(sum(v * v for v in ca.values()))
    norm_b = math.sqrt(sum(v * v for v in cb.values()))

    if not norm_a or not norm_b:
        return 0.0

    return dot / (norm_a * norm_b)


def extract_entities(text):
    text = text or ""

    entities = {}

    employee = re.search(
        r"\bE\d{3,6}\b",
        text,
        re.I
    )

    if employee:
        entities["employee_id"] = employee.group(0).upper()

    dates = re.findall(
        r"\b\d{4}-\d{2}-\d{2}\b",
        text
    )

    if dates:
        entities["dates"] = dates

    salary = re.search(
        r"(?:salary|pay)\s*[:=]?\s*(?:₹|rs\.?|inr)?\s*([\d,]+)",
        text,
        re.I
    )

    if salary:
        entities["salary"] = salary.group(1).replace(",", "")

    leave_types = {
        "casual": "CASUAL",
        "sick": "SICK",
        "annual": "ANNUAL",
        "earned": "ANNUAL",
    }

    lower = text.lower()

    for word, value in leave_types.items():
        if word in lower:
            entities["leave_type"] = value
            break

    priorities = {
        "high": "HIGH",
        "urgent": "HIGH",
        "medium": "MEDIUM",
        "normal": "MEDIUM",
        "low": "LOW",
    }

    for word, value in priorities.items():
        if re.search(rf"\b{word}\b", lower):
            entities["priority"] = value
            break

    return entities


def classify(text):
    """
    Local NLP classifier.

    No API.
    No Gemini.
    No OpenAI.
    Uses TF-style cosine similarity + keyword reasoning.
    """

    normalized = normalize(text)

    if not normalized:
        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "entities": {}
        }

    scores = defaultdict(float)

    for intent, examples in INTENT_EXAMPLES.items():

        best_score = 0.0

        for example in examples:
            score = similarity(normalized, example)

            if score > best_score:
                best_score = score

        scores[intent] = best_score

    # Additional semantic keyword boosting
    keyword_groups = {
        "salary": {
            "salary",
            "pay",
            "payroll",
            "payslip",
            "deduction",
            "bonus",
            "revision",
        },
        "leave": {
            "leave",
            "vacation",
            "holiday",
            "sick",
            "casual",
            "annual",
        },
        "attendance": {
            "attendance",
            "present",
            "absent",
            "checkin",
            "checkout",
            "punch",
        },
        "task": {
            "task",
            "work",
            "assignment",
            "assigned",
            "pending",
        },
        "employee": {
            "employee",
            "staff",
            "worker",
            "person",
            "manager",
        },
        "policy": {
            "policy",
            "rule",
            "rules",
            "guideline",
        },
        "performance": {
            "performance",
            "score",
            "productivity",
            "rating",
        },
    }

    words = set(tokenize(normalized))

    if words & keyword_groups["salary"]:
        scores["get_payroll"] += 0.15

    if words & keyword_groups["leave"]:
        scores["get_leave_balance"] += 0.12

    if words & keyword_groups["attendance"]:
        scores["get_attendance"] += 0.12

    if words & keyword_groups["task"]:
        scores["get_tasks"] += 0.12

    if words & keyword_groups["policy"]:
        scores["get_policy"] += 0.12

    if words & keyword_groups["performance"]:
        scores["analyze_performance"] += 0.12

    if "assign" in words:
        scores["assign_task"] += 0.30

    if "apply" in words and "leave" in words:
        scores["apply_leave"] += 0.30

    if "approve" in words and "leave" in words:
        scores["approve_leave"] += 0.30

    if "reject" in words and "leave" in words:
        scores["reject_leave"] += 0.30

    if "cancel" in words and "leave" in words:
        scores["cancel_leave"] += 0.30

    if "add" in words and "employee" in words:
        scores["create_employee"] += 0.30

    if "update" in words and "employee" in words:
        scores["update_employee"] += 0.30

    if "delete" in words or "remove" in words:
        if "employee" in words:
            scores["delete_employee"] += 0.30

    if "check" in words and "out" in words:
        scores["check_out"] += 0.40

    if "check" in words and "in" in words:
        scores["mark_attendance"] += 0.40

    if not scores:
        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "entities": extract_entities(text)
        }

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    intent, confidence = ranked[0]

    # Ambiguity protection
    if confidence < 0.18:
        intent = "UNKNOWN"

    return {
        "intent": intent,
        "confidence": round(min(confidence, 1.0), 3),
        "entities": extract_entities(text),
        "alternatives": [
            {
                "intent": name,
                "confidence": round(score, 3)
            }
            for name, score in ranked[1:4]
        ]
    }


def explain(text):
    result = classify(text)

    return {
        "input": text,
        "normalized": normalize(text),
        "tokens": tokenize(text),
        "intent": result["intent"],
        "confidence": result["confidence"],
        "entities": result["entities"],
        "alternatives": result["alternatives"],
        "engine": "NovaNLP Local Semantic Classifier"
    }