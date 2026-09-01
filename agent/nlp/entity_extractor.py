import re

from .date_parser import parse_relative


def extract_entities(text):
    text = (text or "").strip()
    entities = {}

    if not text:
        return entities

    match = re.search(r"\bE\d{3,8}\b", text, re.I)

    if match:
        entities["employee_id"] = match.group().upper()

    match = re.search(
        r"\b(CASUAL|SICK|ANNUAL)\s+(?:leave|leaves)\b",
        text,
        re.I,
    )

    if match:
        entities["leave_type"] = match.group(1).upper()

    try:
        relative_dates = parse_relative(text)

        if isinstance(relative_dates, dict):
            for key, value in relative_dates.items():
                if value is not None:
                    entities[key] = str(value)

    except Exception:
        pass

    patterns = [
        r"\b([A-Za-z]+(?:\s+[A-Za-z]+){0,2})'s\s+"
        r"(?:attendance|attendace|attendence|salary|payroll|tasks|leave)\b",

        r"\b(?:attendance|attendace|attendence|salary|payroll|tasks|leave)"
        r"\s+(?:of|for)\s+"
        r"([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b",

        r"\b(?:show|get|check|find)\s+"
        r"([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+"
        r"(?:attendance|attendace|attendence|salary|payroll|tasks|leave)\b",

        r"\b([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\s+"
        r"(?:ki|ka|ke)\s+"
        r"(?:attendance|attendace|attendence|salary|payroll|tasks|leave)\b",

        r"\b(?:payroll|salary|attendance|tasks|leave)\s+for\s+"
        r"([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b",

        r"\bemployee\s+"
        r"([A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b",
    ]

    ignored = {
        "my",
        "me",
        "mera",
        "meri",
        "mere",
        "i",
        "the",
        "this",
        "that",
        "all",
        "any",
        "employee",
        "employees",
        "staff",
        "team",
        "department",
        "pending",
        "attendance",
        "attendace",
        "attendence",
        "salary",
        "payroll",
        "tasks",
        "task",
        "leave",
        "report",
        "today",
    }

    for pattern in patterns:
        match = re.search(pattern, text, re.I)

        if not match:
            continue

        name = re.sub(
            r"\s+",
            " ",
            match.group(1).strip(),
        )

        words = name.lower().split()

        if not name:
            continue

        if any(word in ignored for word in words):
            continue

        if name.lower() in ignored:
            continue

        entities["employee_name"] = name
        break

    return entities