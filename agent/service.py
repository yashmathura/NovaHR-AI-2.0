import re

from agent.planner import execute_agent_pipeline
from agent.novalm import status as novalm_status
from agent import tools
from agent.memory.context_manager import (
    get_or_create,
    recent_context,
    save_message,
)
from agent.intelligence.orchestrator import (
    enrich,
    classify_advanced,
    get_query_entities,
)
from agent.planning.task_planner import plan
from agent.planning.executor import execute_plan
from agent.analytics.attendance import analytics as attendance_analytics
from agent.analytics.payroll import analytics as payroll_analytics
from agent.rag.service import answer as rag_answer
from agent.permissions import check_permission
from core.models import User, Leave, Task


def _role(user):
    return getattr(
        user,
        "role",
        "EMPLOYEE"
    ).upper()


def _employee_queryset_for(user):
    qs = User.objects.filter(
        is_active=True
    )
    role = _role(user)

    if role == "MANAGER":
        qs = qs.filter(
            department_id=user.department_id
        )

    return qs


def _find_employee(user, entities):
    employee_id = entities.get("employee_id")
    if employee_id:
        return _employee_queryset_for(user).filter(
            employee_id=str(employee_id).strip()
        ).first()

    employee_name = entities.get("employee_name")

    if not employee_name:
        return None

    employee_name = str(
        employee_name
    ).strip()

    if not employee_name:
        return None

    qs = _employee_queryset_for(user)

    exact = qs.filter(
        first_name__iexact=employee_name
    ).first()

    if exact:
        return exact

    exact = qs.filter(
        last_name__iexact=employee_name
    ).first()

    if exact:
        return exact

    parts = employee_name.split()

    if len(parts) >= 2:
        exact = qs.filter(
            first_name__iexact=parts[0],
            last_name__iexact=" ".join(parts[1:])
        ).first()

        if exact:
            return exact

    return qs.filter(
        first_name__icontains=employee_name
    ).first()


def _employee_name(employee):
    return (
        employee.get_full_name().strip()
        or employee.username
        or employee.employee_id
    )


def _attendance_message(employee, data):
    records = data.get("records", [])
    if not records:
        return (
            f"No attendance records were found for "
            f"{_employee_name(employee)} for "
            f"{data.get('month')}/{data.get('year')}."
        )

    present = sum(
        1
        for record in records
        if record.get("status") == "PRESENT"
    )

    absent = sum(
        1
        for record in records
        if record.get("status") == "ABSENT"
    )

    miss_punch = sum(
        1
        for record in records
        if record.get("status") == "MISS_PUNCH"
    )

    return (
        f"Attendance for {_employee_name(employee)}: "
        f"{len(records)} record(s), "
        f"{present} present, "
        f"{absent} absent, "
        f"{miss_punch} miss-punch."
    )


def _resolve_follow_up(message, history):
    text = str(message or "").strip()
    lower = text.lower()
    if not any(word in lower for word in (" his ", " her ", " their ", "what about his", "what about her", "and his", "and her", "his attendance", "her attendance", "his tasks", "her tasks", "his payroll", "her payroll")):
        return text

    for item in reversed(history or []):
        metadata = item.get("metadata") or {}
        employee = metadata.get("employee") or {}
        name = employee.get("name")
        if name:
            normalized = re.sub(r"\b(his|her|their)\b", name, text, flags=re.I)
            if normalized != text:
                return normalized
    return text


def _payroll_message(employee, data):
    if not data.get("found"):
        return data.get(
            "message",
            "No payroll record found."
        )
    return (
        f"Payroll for {_employee_name(employee)} "
        f"({data.get('month')}/{data.get('year')}): "
        f"net ₹{data.get('final_salary')}, "
        f"deductions ₹{data.get('deductions')}, "
        f"bonus ₹{data.get('bonus')}."
    )


class IndependentAgent:

    def process_query(
        self,
        user,
        message,
        conversation_id=None,
    ):
        message = message or ""

        conv = get_or_create(
            user,
            conversation_id
        )

        history = recent_context(conv)
        effective_message = _resolve_follow_up(message, history)

        save_message(
            conv,
            "user",
            message,
            {
                "history_size": len(history)
            }
        )

        advanced = classify_advanced(effective_message)

        role = _role(user)

        if advanced == "attendance_analytics":

            if not check_permission(
                role,
                "get_attendance"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view "
                        "attendance analytics."
                    )
                }

            else:

                data = attendance_analytics()

                result = {
                    "status": "success",
                    "intent": advanced,
                    "data": data,
                    "analytics": {
                        "attendance": data
                    },
                    "message": (
                        f"Attendance analytics: "
                        f"{data.get('attendance_rate', 0)}% present rate "
                        f"across {data.get('total_records', 0)} records "
                        f"({data.get('present', 0)} present, "
                        f"{data.get('absent', 0)} absent, "
                        f"{data.get('miss_punch', 0)} miss-punch)."
                    )
                }

        elif advanced == "low_attendance_employees":

            if not (
                check_permission(
                    role,
                    "get_team_attendance"
                )
                or check_permission(
                    role,
                    "get_attendance"
                )
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view "
                        "employee attendance analysis."
                    )
                }

            else:

                steps = plan(
                    message,
                    advanced
                )

                data = execute_plan(steps)

                low_attendance = data.get(
                    "low_attendance",
                    []
                )

                employees = []

                for item in low_attendance:

                    first_name = item.get(
                        "employee__first_name",
                        item.get("first_name", "")
                    )

                    last_name = item.get(
                        "employee__last_name",
                        item.get("last_name", "")
                    )

                    name = (
                        f"{first_name} {last_name}"
                    ).strip()

                    if not name:
                        name = item.get(
                            "employee_name",
                            item.get(
                                "name",
                                "Unknown Employee"
                            )
                        )

                    attendance_rate = (
                        item.get("attendance_rate")
                        or item.get("rate")
                        or item.get("percentage")
                    )

                    if attendance_rate is not None:
                        employees.append(
                            f"{name} "
                            f"({attendance_rate}% attendance)"
                        )
                    else:
                        employees.append(name)

                count = len(low_attendance)

                if count == 0:

                    message_text = (
                        "Low attendance analysis completed. "
                        "No employees were found below the configured "
                        "attendance threshold."
                    )

                else:

                    message_text = (
                        f"Low attendance analysis completed. "
                        f"Found {count} employee(s) below the attendance "
                        f"threshold: {', '.join(employees)}."
                    )

                result = {
                    "status": "success",
                    "intent": advanced,
                    "plan": [
                        step.intent
                        for step in steps
                    ],
                    "data": data,
                    "message": message_text
                }

        elif advanced == "payroll_analytics":

            if not check_permission(
                role,
                "get_payroll_report"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view "
                        "payroll analytics."
                    )
                }

            else:

                data = payroll_analytics()

                total_net = data.get(
                    "total_net",
                    0
                )

                average_net = data.get(
                    "average_net",
                    0
                )

                result = {
                    "status": "success",
                    "intent": advanced,
                    "data": data,
                    "analytics": {
                        "payroll": data
                    },
                    "message": (
                        f"Payroll analytics: "
                        f"{data.get('records', 0)} record(s), "
                        f"total net ₹{total_net:,}, "
                        f"average net ₹{average_net:,}."
                    )
                }

        elif advanced == "multi_step_low_attendance_tasks":

            if not (
                check_permission(
                    role,
                    "get_team_attendance"
                )
                and check_permission(
                    role,
                    "get_tasks"
                )
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to run "
                        "cross-employee analytics."
                    )
                }

            else:

                steps = plan(
                    message,
                    advanced
                )

                data = execute_plan(steps)

                names = sorted(
                    {
                        (
                            f"{item.get('assigned_to__first_name', '')} "
                            f"{item.get('assigned_to__last_name', '')}"
                        ).strip()

                        for item in data.get(
                            "matches",
                            []
                        )

                        if (
                            item.get(
                                "assigned_to__first_name"
                            )
                            or item.get(
                                "assigned_to__last_name"
                            )
                        )
                    }
                )

                low_attendance_count = len(
                    data.get(
                        "low_attendance",
                        []
                    )
                )

                task_count = len(
                    data.get(
                        "matches",
                        []
                    )
                )

                message_text = (
                    f"Multi-step analysis completed. "
                    f"Found {low_attendance_count} employee(s) below "
                    f"the attendance threshold and "
                    f"{task_count} pending task(s) linked to them."
                )

                if names:
                    message_text += (
                        f" Employees with matches: "
                        f"{', '.join(names)}."
                    )

                result = {
                    "status": "success",
                    "intent": advanced,
                    "plan": [
                        step.intent
                        for step in steps
                    ],
                    "data": data,
                    "message": message_text
                }

        elif advanced == "my_attendance":

            if not check_permission(
                role,
                "get_attendance"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view attendance."
                    )
                }

            else:

                data = tools.get_attendance(user)

                result = {
                    "status": "success",
                    "intent": advanced,
                    "data": data,
                    "message": _attendance_message(
                        user,
                        data
                    )
                }

        elif advanced == "my_payroll":

            if not check_permission(
                role,
                "get_payroll"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view payroll."
                    )
                }

            else:

                data = tools.get_payroll(user)

                result = {
                    "status": (
                        "success"
                        if data.get("found")
                        else "error"
                    ),
                    "intent": advanced,
                    "data": data,
                    "message": _payroll_message(
                        user,
                        data
                    )
                }

        elif advanced == "employee_attendance":

            entities = get_query_entities(effective_message)

            employee = _find_employee(
                user,
                entities
            )

            if not employee:

                result = {
                    "status": "error",
                    "intent": advanced,
                    "message": (
                        "Employee could not be identified."
                    )
                }

            elif not check_permission(
                role,
                "get_team_attendance"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view "
                        "this employee's attendance."
                    )
                }

            else:

                data = tools.get_attendance(employee)

                result = {
                    "status": "success",
                    "intent": advanced,
                    "employee": {
                        "employee_id": employee.employee_id,
                        "name": _employee_name(employee),
                    },
                    "data": data,
                    "message": _attendance_message(
                        employee,
                        data
                    )
                }

        elif advanced == "employee_payroll":

            entities = get_query_entities(effective_message)

            employee = _find_employee(
                user,
                entities
            )

            if not employee:

                result = {
                    "status": "error",
                    "intent": advanced,
                    "message": (
                        "Employee could not be identified."
                    )
                }

            elif not check_permission(
                role,
                "get_payroll"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view "
                        "this employee's payroll."
                    )
                }

            else:

                data = tools.get_payroll(
                    user,
                    employee_id=employee.employee_id
                )

                result = {
                    "status": (
                        "success"
                        if data.get("found")
                        else "error"
                    ),
                    "intent": advanced,
                    "employee": {
                        "employee_id": employee.employee_id,
                        "name": _employee_name(employee),
                    },
                    "data": data,
                    "message": _payroll_message(
                        employee,
                        data
                    )
                }

        elif advanced == "employee_tasks":

            entities = get_query_entities(effective_message)

            employee = _find_employee(
                user,
                entities
            )

            if not employee:

                result = {
                    "status": "error",
                    "intent": advanced,
                    "message": (
                        "Employee could not be identified."
                    )
                }

            elif not check_permission(
                role,
                "get_tasks"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view "
                        "this employee's tasks."
                    )
                }

            else:

                task_qs = Task.objects.filter(
                    assigned_to=employee
                )

                if role == "MANAGER":
                    task_qs = task_qs.filter(
                        assigned_to__department_id=user.department_id
                    )

                tasks = [
                    {
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "priority": task.priority,
                        "due_date": (
                            str(task.due_date)
                            if task.due_date
                            else None
                        ),
                    }
                    for task in task_qs.order_by(
                        "status",
                        "due_date"
                    )[:50]
                ]

                result = {
                    "status": "success",
                    "intent": advanced,
                    "employee": {
                        "employee_id": employee.employee_id,
                        "name": _employee_name(employee),
                    },
                    "data": {
                        "count": len(tasks),
                        "tasks": tasks,
                    },
                    "message": (
                        f"{_employee_name(employee)} has "
                        f"{len(tasks)} task(s)."
                    )
                }

        elif advanced == "employee_leave":

            entities = get_query_entities(effective_message)

            employee = _find_employee(
                user,
                entities
            )

            if not employee:

                result = {
                    "status": "error",
                    "intent": advanced,
                    "message": (
                        "Employee could not be identified."
                    )
                }

            elif not check_permission(
                role,
                "get_team_attendance"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view "
                        "this employee's leave information."
                    )
                }

            else:

                leave_qs = Leave.objects.filter(
                    employee=employee
                ).order_by(
                    "-start_date"
                )

                leaves = [
                    {
                        "id": leave.id,
                        "type": leave.leave_type,
                        "status": leave.status,
                        "start_date": str(
                            leave.start_date
                        ),
                        "end_date": str(
                            leave.end_date
                        ),
                        "days": leave.days,
                    }
                    for leave in leave_qs[:50]
                ]

                result = {
                    "status": "success",
                    "intent": advanced,
                    "employee": {
                        "employee_id": employee.employee_id,
                        "name": _employee_name(employee),
                    },
                    "data": {
                        "count": len(leaves),
                        "leaves": leaves,
                    },
                    "message": (
                        f"{_employee_name(employee)} has "
                        f"{len(leaves)} leave record(s)."
                    )
                }

        elif advanced == "explain_salary_change":

            if not check_permission(
                role,
                "get_payroll"
            ):

                result = {
                    "status": "denied",
                    "intent": advanced,
                    "message": (
                        "You are not authorized to view payroll."
                    )
                }

            else:

                data = tools.explain_salary_change(user)

                if not data.get("found"):

                    result = {
                        "status": "error",
                        "intent": advanced,
                        "data": data,
                        "message": data.get(
                            "message",
                            "No payroll information found."
                        )
                    }

                else:

                    reasons = data.get(
                        "reasons",
                        []
                    )

                    result = {
                        "status": "success",
                        "intent": advanced,
                        "data": data,
                        "message": (
                            f"Your salary changed from "
                            f"₹{data.get('previous_salary')} "
                            f"({data.get('previous_period')}) to "
                            f"₹{data.get('current_salary')} "
                            f"({data.get('current_period')}). "
                            f"Difference: ₹{data.get('difference')}. "
                            f"Possible reasons: "
                            f"{'; '.join(reasons)}."
                        )
                    }

        elif advanced == "rag_policy":

            data = rag_answer(effective_message)

            result = {
                "status": "success",
                "intent": "rag_policy",
                "data": data,
                "message": data.get(
                    "answer",
                    "No relevant policy information was found."
                )
            }

        else:

            result = execute_agent_pipeline(
                user,
                effective_message
            )

        result = enrich(
            effective_message,
            result
        )

        result["engine"] = (
            "NovaHR AI 2.0 • Local NLP • Planner • "
            "RAG • Analytics • Memory"
        )

        result["conversation_id"] = str(
            conv.id
        )

        result["history_used"] = len(history)

        result["agent_status"] = (
            "completed"
            if result.get("status") == "success"
            else result.get("status", "error")
        )

        save_message(
            conv,
            "assistant",
            result.get("message", ""),
            {
                "intent": result.get("intent"),
                "status": result.get("status"),
                "history_used": len(history),
                "employee": result.get("employee") or {},
            }
        )

        return result


def model_status(self):
    return novalm_status()


def run_agent(
    user,
    message,
    conversation_id=None,
):
    return IndependentAgent().process_query(
        user,
        message,
        conversation_id
    )