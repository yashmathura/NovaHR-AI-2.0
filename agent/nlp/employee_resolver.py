from difflib import SequenceMatcher
from django.db.models import Q

from core.models import User


def employee_data(user):
    """
    Convert a User object into safe employee data.
    """

    return {
        "id": user.id,
        "employee_id": user.employee_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name().strip(),
        "username": user.username,
        "role": user.role,
        "job_title": user.job_title,
    }


def similarity(a, b):
    """
    Return similarity score between two strings.
    """

    return SequenceMatcher(
        None,
        (a or "").lower(),
        (b or "").lower()
    ).ratio()


def resolve_employee(query):
    """
    Resolve an employee using:

    - Employee ID
    - First name
    - Last name
    - Full name
    - Username
    - Partial matches
    - Typo/fuzzy matching
    """

    query = (query or "").strip()

    if not query:
        return {
            "status": "not_found",
            "employee": None,
            "matches": [],
        }

    normalized = " ".join(query.split())

    # --------------------------------------------------
    # Exact employee ID
    # --------------------------------------------------

    employee = User.objects.filter(
        employee_id__iexact=normalized
    ).first()

    if employee:
        return {
            "status": "found",
            "employee": employee_data(employee),
            "matches": [],
            "match_type": "employee_id",
        }

    # --------------------------------------------------
    # Exact username
    # --------------------------------------------------

    employee = User.objects.filter(
        username__iexact=normalized
    ).first()

    if employee:
        return {
            "status": "found",
            "employee": employee_data(employee),
            "matches": [],
            "match_type": "username",
        }

    # --------------------------------------------------
    # Search database fields
    # --------------------------------------------------

    candidates = User.objects.filter(
        Q(first_name__icontains=normalized)
        | Q(last_name__icontains=normalized)
        | Q(username__icontains=normalized)
        | Q(employee_id__icontains=normalized)
    )

    # --------------------------------------------------
    # Full name matching
    # --------------------------------------------------

    full_name_matches = []

    for user in User.objects.all():

        full_name = user.get_full_name().strip()

        if full_name and normalized.lower() == full_name.lower():

            full_name_matches.append(user)

    if len(full_name_matches) == 1:

        employee = full_name_matches[0]

        return {
            "status": "found",
            "employee": employee_data(employee),
            "matches": [],
            "match_type": "full_name",
        }

    # --------------------------------------------------
    # Partial database matches
    # --------------------------------------------------

    candidate_list = list(candidates)

    # Avoid duplicates

    seen = set()
    unique_candidates = []

    for user in candidate_list:

        if user.id not in seen:

            seen.add(user.id)
            unique_candidates.append(user)

    if len(unique_candidates) == 1:

        employee = unique_candidates[0]

        return {
            "status": "found",
            "employee": employee_data(employee),
            "matches": [],
            "match_type": "partial_match",
        }

    if len(unique_candidates) > 1:

        return {
            "status": "ambiguous",
            "employee": None,
            "matches": [
                employee_data(user)
                for user in unique_candidates[:5]
            ],
        }

    # --------------------------------------------------
    # Fuzzy matching for typos
    # --------------------------------------------------

    scored_matches = []

    for user in User.objects.all():

        full_name = user.get_full_name().strip()

        fields = [
            full_name,
            user.first_name,
            user.last_name,
            user.username,
            user.employee_id,
        ]

        score = max(
            similarity(normalized, field)
            for field in fields
            if field
        )

        if score >= 0.70:

            scored_matches.append(
                (score, user)
            )

    scored_matches.sort(
        key=lambda item: item[0],
        reverse=True
    )

    if len(scored_matches) == 1:

        score, employee = scored_matches[0]

        return {
            "status": "found",
            "employee": employee_data(employee),
            "matches": [],
            "match_type": "fuzzy_match",
            "confidence": round(score, 2),
        }

    if len(scored_matches) > 1:

        best_score = scored_matches[0][0]

        # If the best result is clearly better
        # than the second result, use it.

        second_score = scored_matches[1][0]

        if best_score - second_score >= 0.10:

            score, employee = scored_matches[0]

            return {
                "status": "found",
                "employee": employee_data(employee),
                "matches": [],
                "match_type": "fuzzy_match",
                "confidence": round(score, 2),
            }

        return {
            "status": "ambiguous",
            "employee": None,
            "matches": [
                {
                    **employee_data(user),
                    "confidence": round(score, 2),
                }
                for score, user in scored_matches[:5]
            ],
        }

    # --------------------------------------------------
    # Nothing found
    # --------------------------------------------------

    return {
        "status": "not_found",
        "employee": None,
        "matches": [],
    }