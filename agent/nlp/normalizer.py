import re


HINDI_HINTS = {
    "dikhao": "show",
    "dikhana": "show",
    "batao": "tell",
    "bata": "tell",

    "ki attendance": "attendance of",
    "ka attendance": "attendance of",

    "ki salary": "salary of",
    "ka salary": "salary of",

    "ki leave": "leave of",
    "ka leave": "leave of",

    "meri": "my",
    "mera": "my",
    "mere": "my",

    "chhutti": "leave",
    "tankha": "salary",
}


COMMON_TYPOS = {
    "attendace": "attendance",
    "attendence": "attendance",
    "attendencee": "attendance",
    "atendance": "attendance",
    "attendnace": "attendance",

    "sallary": "salary",
    "salery": "salary",

    "payrol": "payroll",

    "tomorow": "tomorrow",
    "tommorow": "tomorrow",
}


def normalize_query(text):

    s = (text or "").lower().strip()

    # Fix common typos first
    for wrong, correct in COMMON_TYPOS.items():

        s = re.sub(
            rf"\b{re.escape(wrong)}\b",
            correct,
            s
        )

    # Hindi / Hinglish replacements
    for hindi, english in HINDI_HINTS.items():

        s = s.replace(hindi, english)

    # Normalize spaces
    s = re.sub(r"\s+", " ", s)

    return s.strip()