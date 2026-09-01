import re
from agent.router import (
    resolve_intent,
    extract_employee_id,
    extract_leave_type,
    extract_dates,
    extract_status,
    extract_priority,
    extract_kv,
)
from agent.permissions import check_permission
from agent import tools
from core.models import (
    AgentAuditLog,
    Leave,
)


def _role(user):
    return getattr(
        user,
        "role",
        "EMPLOYEE"
    ).upper()


def _missing_message(intent):
    messages = {
        "create_employee": (
            "To add an employee, provide name and email. "
            "Example: add employee name: Rahul Kumar, "
            "email: rahul@company.com, salary: 45000, "
            "department: Engineering, job_title: Developer"
        ),
        "apply_leave": (
            "To apply leave, provide dates and reason. "
            "Example: apply sick leave from 2026-08-28 "
            "to 2026-08-29, reason: fever"
        ),
        "assign_task": (
            "To assign a task, provide employee ID and title. "
            "Example: assign task to E1005 "
            "title: Prepare report, due_date: 2026-09-01, "
            "priority: HIGH"
        ),
    }
    return messages.get(
        intent,
        "I need a little more information to complete that request."
    )


def _pretty(intent, data):
    data = data or {}
    if intent == "get_leave_balance":
        balances = data.get(
            "balances",
            {}
        )

        if not balances:
            return "No leave balance information was found."

        return (
            "Leave balance:\n"
            + "\n".join(
                (
                    f"• {key.title()}: "
                    f"{value['remaining']} remaining "
                    f"({value['used']} used / "
                    f"{value['allocated']} allocated)"
                )
                for key, value in balances.items()
            )
        )

    if intent == "salary_revision":
        revision = data.get(
            "last_salary_revision"
        )

        if not revision:
            return (
                "No salary revision date is recorded "
                "for your profile."
            )

        return (
            f"Your last salary revision was on "
            f"{revision}."
        )

    if intent in {
        "get_attendance",
        "get_team_attendance",
    }:
        records = data.get(
            "records",
            []
        )

        return (
            f"Attendance checked for "
            f"{data.get('month', 'today')}/"
            f"{data.get('year', '')}. "
            f"{len(records)} record(s) found."
        )

    if intent in {
        "get_payroll",
        "get_payroll_report",
    }:
        if intent == "get_payroll":
            return (
                f"Payroll for {data.get('employee')}: "
                f"net ₹{data.get('final_salary')}, "
                f"deductions ₹{data.get('deductions')}, "
                f"bonus ₹{data.get('bonus')}."
            )

        return (
            f"Payroll report: "
            f"{data.get('count', 0)} records, "
            f"total net ₹{data.get('total_net_salary', 0)}."
        )

    if intent == "generate_payroll":
        return (
            f"Payroll generated for "
            f"{data.get('count', 0)} employee(s) "
            f"for {data.get('period')}."
        )

    if intent == "get_tasks":
        return (
            f"You have/accessed "
            f"{data.get('count', 0)} task(s)."
        )

    if intent == "list_employees":
        return (
            f"There are {data.get('count', 0)} "
            f"active employees in your permitted scope."
        )

    if intent == "get_employee":
        return (
            f"Employee {data.get('employee_id')}: "
            f"{data.get('name')}, "
            f"{data.get('job_title') or 'No title'}, "
            f"{data.get('department') or 'No department'}."
        )

    if intent == "analyze_performance":
        return (
            f"Performance score: "
            f"{data.get('performance_score')}%. "
            f"Attendance: "
            f"{data.get('attendance_percent')}%. "
            f"Task completion: "
            f"{data.get('task_completion_percent')}%."
        )

    if intent == "team_performance":
        return (
            f"Performance report generated for "
            f"{len(data.get('employees', []))} employee(s)."
        )

    if intent == "list_pending_leaves":
        return f"Found {data.get('count', 0)} pending leave request(s)."

    if intent == "get_policy":
        return (
            f"Found {len(data.get('results', []))} "
            f"matching policy document(s)."
        )

    if intent == "get_notifications":
        return (
            f"You have {data.get('count', 0)} "
            f"unread notification(s)."
        )

    if intent == "explain_salary_change":
        if not data.get("found"):
            return data.get(
                "message",
                "No payroll information found."
            )

        reasons = data.get(
            "reasons",
            []
        )

        return (
            f"Your salary changed from "
            f"₹{data.get('previous_salary')} "
            f"({data.get('previous_period')}) to "
            f"₹{data.get('current_salary')} "
            f"({data.get('current_period')}). "
            f"Difference: ₹{data.get('difference')}. "
            f"Reasons: {'; '.join(reasons)}."
        )

    if data.get("last_salary_revision"):
        return (
            f"Your latest salary revision was on "
            f"{data['last_salary_revision']}. "
            f"Your current/latest net salary is "
            f"₹{data.get('final_salary')}."
        )

    return data.get(
        "message",
        "Done successfully."
    )


def recover_id(text):
    match = re.search(
        r"\b(?:leave|task|id)\s*#?\s*(\d+)\b",
        text or "",
        re.I,
    )
    return (
        match.group(1)
        if match
        else None
    )


def execute_agent_pipeline(user, message):
    intent = resolve_intent(message)
    role = _role(user)
    if intent == "UNKNOWN":
        return {
            "status": "error",
            "intent": intent,
            "message": (
                "I couldn't identify that request. "
                "Try leave, attendance, salary, payroll, "
                "tasks, policies, performance, employees, "
                "or notifications."
            )
        }

    if not check_permission(
        role,
        intent
    ):
        return {
            "status": "denied",
            "intent": intent,
            "message": (
                f"Security Alert: {role} is not authorized "
                f"to perform '{intent}'."
            )
        }

    kv = extract_kv(message)

    emp_id = extract_employee_id(message)

    start_date, end_date = extract_dates(message)

    leave_type = extract_leave_type(message)

    status = extract_status(message)

    priority = extract_priority(message)

    try:
        if intent == "get_leave_balance":
            data = tools.get_leave_balance(
                user,
                leave_type
                if leave_type in {
                    "CASUAL",
                    "SICK",
                    "ANNUAL",
                }
                else "ALL"
            )

        elif intent == "apply_leave":
            if not start_date:
                return {
                    "status": "need_input",
                    "intent": intent,
                    "message": _missing_message(intent),
                }

            data = tools.apply_leave(
                user,
                leave_type,
                str(start_date),
                str(end_date),
                kv.get("reason")
                or "Requested through NovaHR Agent",
            )

        elif intent == "cancel_leave":
            leave_id = int(
                recover_id(message) or 0
            )

            data = (
                tools.cancel_leave(
                    user,
                    leave_id
                )
                if leave_id
                else {
                    "success": False,
                    "error": (
                        "Provide the leave ID to cancel."
                    )
                }
            )

        elif intent == "get_attendance":
            data = tools.get_attendance(user)

        elif intent == "mark_attendance":
            data = tools.mark_attendance(user)

        elif intent == "check_out":
            data = tools.check_out(user)

        elif intent == "get_team_attendance":
            data = tools.get_team_attendance(user)

        elif intent == "get_payroll":
            data = tools.get_payroll(
                user,
                employee_id=emp_id
            )

        elif intent == "salary_revision":
            data = tools.get_payroll(user)

        elif intent == "explain_salary_change":
            data = tools.explain_salary_change(user)

        elif intent == "get_payroll_report":
            data = tools.get_payroll_report(user)

        elif intent == "generate_payroll":
            data = tools.generate_payroll(
                user,
                employee_id=emp_id
            )

        elif intent == "get_tasks":
            data = tools.get_tasks(
                user,
                status or "ALL"
            )

        elif intent == "assign_task":
            if (
                not emp_id
                or not kv.get("title")
            ):
                return {
                    "status": "need_input",
                    "intent": intent,
                    "message": _missing_message(intent),
                }

            data = tools.assign_task(
                user,
                emp_id,
                kv["title"],
                kv.get("description", ""),
                kv.get("due_date"),
                priority,
            )

        elif intent == "update_task":
            task_id = int(
                recover_id(message) or 0
            )

            data = (
                tools.update_task(
                    user,
                    task_id,
                    status or "DONE"
                )
                if task_id
                else {
                    "success": False,
                    "error": (
                        "Provide task ID, "
                        "e.g. task 12 done."
                    )
                }
            )

        elif intent == "list_pending_leaves":
            data = tools.list_pending_leaves(user)

        elif intent == "get_policy":
            data = tools.get_policy(
                user,
                message
            )

        elif intent == "analyze_performance":
            data = tools.analyze_performance(user)

        elif intent == "team_performance":
            data = tools.team_performance(user)

        elif intent == "list_employees":
            data = tools.list_employees(user)

        elif intent == "get_employee":
            data = (
                tools.get_employee(
                    user,
                    emp_id
                )
                if emp_id
                else {
                    "found": False,
                    "message": (
                        "Provide employee ID such as E1005."
                    )
                }
            )

        elif intent == "create_employee":
            if (
                not kv.get("name")
                or not kv.get("email")
            ):
                return {
                    "status": "need_input",
                    "intent": intent,
                    "message": _missing_message(intent),
                }

            data = tools.create_employee(
                user,
                kv["name"],
                kv["email"],
                kv.get(
                    "password",
                    "Employee@123"
                ),
                kv.get(
                    "role",
                    "EMPLOYEE"
                ).upper(),
                kv.get("employee_id"),
                kv.get("department"),
                kv.get("salary", "0"),
                kv.get("job_title", ""),
                kv.get("phone", ""),
            )

        elif intent == "update_employee":
            if not emp_id:
                return {
                    "status": "need_input",
                    "intent": intent,
                    "message": (
                        "Provide employee ID, e.g. "
                        "update employee E1005 "
                        "salary: 50000, "
                        "job_title: Senior Developer"
                    ),
                }

            data = tools.update_employee(
                user,
                emp_id,
                **kv
            )

        elif intent == "delete_employee":
            data = (
                tools.delete_employee(
                    user,
                    emp_id
                )
                if emp_id
                else {
                    "success": False,
                    "error": "Provide employee ID."
                }
            )

        elif intent in {
            "approve_leave",
            "reject_leave",
        }:
            leave_id = int(
                recover_id(message) or 0
            )

            if not leave_id:
                pending = Leave.objects.filter(
                    status="PENDING"
                )

                if role == "MANAGER":
                    pending = pending.filter(
                        employee__department_id=user.department_id
                    )

                leave = pending.order_by(
                    "applied_at"
                ).first()

                leave_id = (
                    leave.id
                    if leave
                    else 0
                )

            if leave_id:
                handler = (
                    tools.approve_leave
                    if intent == "approve_leave"
                    else tools.reject_leave
                )

                data = handler(
                    user,
                    leave_id
                )

            else:
                data = {
                    "success": False,
                    "error": (
                        "No pending leave request found."
                    )
                }

        elif intent == "send_notification":
            if (
                not emp_id
                or not kv.get("title")
                or not kv.get("message")
            ):
                return {
                    "status": "need_input",
                    "intent": intent,
                    "message": (
                        "Provide employee ID plus title and message. "
                        "Example: notify E1005 title: Meeting, "
                        "message: Meeting at 3 PM."
                    ),
                }

            data = tools.send_notification(
                user,
                emp_id,
                kv["title"],
                kv["message"],
            )

        elif intent == "get_notifications":
            data = tools.get_notifications(user)

        elif intent == "mark_notifications_read":
            data = tools.mark_notifications_read(user)

        elif intent == "profile":
            data = tools.profile(user)

        elif intent == "department_summary":
            data = tools.department_summary(user)

        else:
            return {
                "status": "error",
                "intent": intent,
                "message": "Tool not implemented."
            }

        ok = not (
            isinstance(data, dict)
            and (
                data.get("success") is False
                or data.get("found") is False
            )
        )

        AgentAuditLog.objects.create(
            user=user,
            tool_name=intent,
            arguments={
                "message": message
            },
            result=data,
            success=ok,
        )

        return {
            "status": "success" if ok else "error",
            "intent": intent,
            "data": data,
            "message": (
                _pretty(intent, data)
                if ok
                else data.get("error")
                or data.get("message")
                or "Request could not be completed."
            )
        }

    except Exception as exc:
        AgentAuditLog.objects.create(
            user=user,
            tool_name=intent,
            arguments={
                "message": message
            },
            result={
                "error": str(exc)
            },
            success=False,
        )

        return {
            "status": "error",
            "intent": intent,
            "message": (
                f"I could not complete that safely: {exc}"
            )
        }