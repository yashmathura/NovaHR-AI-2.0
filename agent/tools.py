from datetime import date
from decimal import Decimal, InvalidOperation
import secrets
import string

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.models import (
    User,
    Attendance,
    Payroll,
    Task,
    KnowledgeDocument,
    Notification,
    Leave,
    Department,
)


def _role(user):
    return str(getattr(user, "role", "EMPLOYEE")).upper()


def _employee_name(user):
    return user.get_full_name().strip() or user.username


def _employees_for(user):
    role = _role(user)

    queryset = User.objects.filter(
        is_active=True
    )

    if role == "MANAGER":
        queryset = queryset.filter(
            department_id=user.department_id
        )

    return queryset


def _can_manage_employee(user, employee):
    role = _role(user)

    if role in {"ADMIN", "HR"}:
        return True

    if role == "MANAGER":
        return (
            user.department_id
            and employee.department_id == user.department_id
        )

    return employee.id == user.id


def _temporary_password(length=12):
    alphabet = (
        string.ascii_letters
        + string.digits
        + "@#$%"
    )

    while True:
        password = "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
        ):
            return password


def _safe_decimal(value, default=None):
    try:
        return Decimal(str(value))
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return default


def _attendance_payload(record):
    return {
        "date": str(record.date),
        "status": record.status,
        "check_in": (
            record.check_in.isoformat()
            if record.check_in
            else None
        ),
        "check_out": (
            record.check_out.isoformat()
            if record.check_out
            else None
        ),
        "hours": record.hours_worked,
    }


def get_leave_balance(user, leave_type="ALL"):
    mapping = {
        "CASUAL": "casual_leave_quota",
        "SICK": "sick_leave_quota",
        "ANNUAL": "annual_leave_quota",
    }

    leave_type = str(leave_type or "ALL").upper()

    leave_types = (
        [leave_type]
        if leave_type in mapping
        else list(mapping.keys())
    )

    balances = {}

    for kind in leave_types:
        quota = getattr(
            user,
            mapping[kind],
            0,
        ) or 0

        used_days = sum(
            leave.days
            for leave in Leave.objects.filter(
                employee=user,
                leave_type=kind,
                status="APPROVED",
            )
        )

        balances[kind] = {
            "allocated": quota,
            "used": used_days,
            "remaining": max(
                0,
                quota - used_days,
            ),
        }

    return {
        "found": True,
        "balances": balances,
    }


def get_attendance(
    user,
    month=None,
    year=None,
):
    today = timezone.localdate()

    month = int(month or today.month)
    year = int(year or today.year)

    if month < 1 or month > 12:
        return {
            "found": False,
            "message": "Invalid month.",
        }

    queryset = Attendance.objects.filter(
        employee=user,
        date__year=year,
        date__month=month,
    ).order_by("date")

    return {
        "found": True,
        "month": month,
        "year": year,
        "records": [
            _attendance_payload(record)
            for record in queryset
        ],
    }


def mark_attendance(user):
    today = timezone.localdate()
    now = timezone.localtime()

    attendance, created = (
        Attendance.objects.get_or_create(
            employee=user,
            date=today,
            defaults={
                "status": "PRESENT",
                "check_in": now,
            },
        )
    )

    if not created and attendance.check_in:
        return {
            "success": False,
            "message": (
                "Already checked in at "
                f"{attendance.check_in.isoformat()}."
            ),
        }

    if not created:
        attendance.check_in = now
        attendance.status = "PRESENT"

        attendance.save(
            update_fields=[
                "check_in",
                "status",
            ]
        )

    return {
        "success": True,
        "message": "Attendance marked successfully.",
        "date": str(today),
        "check_in": now.isoformat(),
    }


def check_out(user):
    attendance = Attendance.objects.filter(
        employee=user,
        date=timezone.localdate(),
    ).first()

    if not attendance or not attendance.check_in:
        return {
            "success": False,
            "message": "Please check in first.",
        }

    if attendance.check_out:
        return {
            "success": False,
            "message": "Already checked out.",
        }

    attendance.check_out = timezone.localtime()
    attendance.save(
        update_fields=["check_out"]
    )

    attendance.refresh_from_db()

    return {
        "success": True,
        "message": "Checked out successfully.",
        "check_out": attendance.check_out.isoformat(),
        "hours": attendance.hours_worked,
    }


def get_team_attendance(user):
    role = _role(user)
    today = timezone.localdate()

    if role == "MANAGER":
        employees = User.objects.filter(
            is_active=True,
            role="EMPLOYEE",
            department_id=user.department_id,
        )
    elif role in {
        "ADMIN",
        "HR",
        "FINANCE",
    }:
        employees = User.objects.filter(
            is_active=True,
            role="EMPLOYEE",
        )
    else:
        return {
            "found": False,
            "message": (
                "You are not authorized to view "
                "team attendance."
            ),
        }

    attendance_map = {
        record.employee_id: record
        for record in Attendance.objects.filter(
            employee__in=employees,
            date=today,
        )
    }

    records = []

    for employee in employees.select_related(
        "department"
    ).order_by("employee_id"):
        attendance = attendance_map.get(
            employee.id
        )

        records.append(
            {
                "employee_id": employee.employee_id,
                "name": _employee_name(employee),
                "status": (
                    attendance.status
                    if attendance
                    else "ABSENT"
                ),
                "check_in": (
                    attendance.check_in.isoformat()
                    if attendance
                    and attendance.check_in
                    else None
                ),
                "check_out": (
                    attendance.check_out.isoformat()
                    if attendance
                    and attendance.check_out
                    else None
                ),
            }
        )

    return {
        "found": True,
        "date": str(today),
        "count": len(records),
        "records": records,
    }


def get_payroll(
    user,
    month=None,
    year=None,
    employee_id=None,
):
    role = _role(user)
    target = user

    if employee_id:
        if role not in {
            "HR",
            "FINANCE",
            "ADMIN",
        }:
            return {
                "found": False,
                "message": (
                    "You are not authorized to view "
                    "another employee's payroll."
                ),
            }

        target = User.objects.filter(
            employee_id=employee_id,
            is_active=True,
        ).first()

        if not target:
            return {
                "found": False,
                "message": "Employee not found.",
            }

    queryset = Payroll.objects.filter(
        employee=target
    ).order_by(
        "-year",
        "-month",
    )

    if month is not None and year is not None:
        queryset = queryset.filter(
            month=int(month),
            year=int(year),
        )

    payroll = queryset.first()

    if not payroll:
        return {
            "found": False,
            "message": (
                "No payroll record found for "
                f"{_employee_name(target)}."
            ),
        }

    return {
        "found": True,
        "employee_id": target.employee_id,
        "employee": _employee_name(target),
        "month": payroll.month,
        "year": payroll.year,
        "base_salary": str(payroll.base_salary),
        "present_days": str(payroll.present_days),
        "absent_days": str(payroll.absent_days),
        "leave_days": str(payroll.leave_days),
        "deductions": str(payroll.deductions),
        "bonus": str(payroll.bonus),
        "final_salary": str(payroll.final_salary),
        "last_salary_revision": (
            str(target.last_salary_revision)
            if getattr(
                target,
                "last_salary_revision",
                None,
            )
            else None
        ),
    }


def get_payroll_report(user):
    role = _role(user)

    if role in {
        "FINANCE",
        "ADMIN",
    }:
        queryset = Payroll.objects.select_related(
            "employee"
        )

    elif role == "HR":
        queryset = Payroll.objects.select_related(
            "employee"
        )

        if user.department_id:
            queryset = queryset.filter(
                employee__department_id=user.department_id
            )

    else:
        return {
            "found": False,
            "message": (
                "You are not authorized to view "
                "payroll reports."
            ),
        }

    total = (
        queryset.aggregate(
            total=Sum("final_salary")
        )["total"]
        or Decimal("0")
    )

    records = list(
        queryset.order_by(
            "-year",
            "-month",
            "employee__employee_id",
        )[:200]
    )

    return {
        "found": True,
        "count": len(records),
        "total_net_salary": str(total),
        "records": [
            {
                "employee_id": payroll.employee.employee_id,
                "employee": _employee_name(
                    payroll.employee
                ),
                "period": (
                    f"{payroll.month}/{payroll.year}"
                ),
                "net": str(payroll.final_salary),
                "deductions": str(
                    payroll.deductions
                ),
                "bonus": str(payroll.bonus),
            }
            for payroll in records
        ],
    }


@transaction.atomic
def generate_payroll(
    user,
    employee_id=None,
    month=None,
    year=None,
):
    role = _role(user)

    if role not in {
        "FINANCE",
        "ADMIN",
    }:
        return {
            "success": False,
            "error": (
                "You are not authorized to generate "
                "payroll."
            ),
        }

    today = timezone.localdate()

    month = int(month or today.month)
    year = int(year or today.year)

    if month < 1 or month > 12:
        return {
            "success": False,
            "error": "Invalid payroll month.",
        }

    employees = User.objects.filter(
        role="EMPLOYEE",
        is_active=True,
    )

    if employee_id:
        employees = employees.filter(
            employee_id=employee_id
        )

    if not employees.exists():
        return {
            "success": False,
            "error": "No eligible employees found.",
        }

    created = []

    for employee in employees.select_for_update():

        attendance_records = (
            Attendance.objects.filter(
                employee=employee,
                date__year=year,
                date__month=month,
            )
        )

        present = attendance_records.filter(
            status="PRESENT"
        ).count()

        absent = attendance_records.filter(
            status="ABSENT"
        ).count()

        approved_leave_days = sum(
            leave.days
            for leave in Leave.objects.filter(
                employee=employee,
                status="APPROVED",
                start_date__year=year,
                start_date__month=month,
            )
        )

        payroll, _ = (
            Payroll.objects.update_or_create(
                employee=employee,
                month=month,
                year=year,
                defaults={
                    "base_salary": employee.salary,
                    "working_days": 22,
                    "present_days": present,
                    "absent_days": absent,
                    "leave_days": approved_leave_days,
                },
            )
        )

        created.append(
            {
                "employee_id": employee.employee_id,
                "final_salary": str(
                    payroll.final_salary
                ),
            }
        )

    return {
        "success": True,
        "period": f"{month}/{year}",
        "count": len(created),
        "records": created,
    }


def get_tasks(user, status="ALL"):
    role = _role(user)
    status = str(status or "ALL").upper()

    if role == "EMPLOYEE":
        queryset = Task.objects.filter(
            assigned_to=user
        )

    elif role == "MANAGER":
        queryset = Task.objects.filter(
            assigned_to__department_id=user.department_id
        )

    else:
        queryset = Task.objects.all()

    if status != "ALL":
        queryset = queryset.filter(
            status=status
        )

    tasks = queryset.select_related(
        "assigned_to"
    ).order_by(
        "status",
        "due_date",
        "id",
    )[:50]

    return {
        "count": queryset.count(),
        "tasks": [
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
                "assigned_to": (
                    task.assigned_to.employee_id
                ),
            }
            for task in tasks
        ],
    }


@transaction.atomic
def assign_task(
    user,
    employee_id,
    title,
    description="",
    due_date=None,
    priority="MEDIUM",
):
    role = _role(user)

    if role not in {
        "MANAGER",
        "HR",
        "ADMIN",
    }:
        return {
            "success": False,
            "error": (
                "You are not authorized to assign tasks."
            ),
        }

    employee = User.objects.filter(
        employee_id=employee_id,
        role="EMPLOYEE",
        is_active=True,
    ).first()

    if not employee:
        return {
            "success": False,
            "error": "Employee not found.",
        }

    if (
        role == "MANAGER"
        and employee.department_id != user.department_id
    ):
        return {
            "success": False,
            "error": (
                "Employee is outside your department."
            ),
        }

    parsed_due_date = None

    if due_date:
        try:
            parsed_due_date = date.fromisoformat(
                str(due_date)
            )
        except ValueError:
            return {
                "success": False,
                "error": "Invalid due date.",
            }

    priority = str(
        priority or "MEDIUM"
    ).upper()

    task = Task.objects.create(
        assigned_to=employee,
        assigned_by=user,
        title=str(title).strip(),
        description=str(description or "").strip(),
        due_date=parsed_due_date,
        priority=priority,
    )

    Notification.objects.create(
        employee=employee,
        title="New task assigned",
        message=(
            f"{task.title} ({priority}) "
            "was assigned to you."
        ),
    )

    return {
        "success": True,
        "task_id": task.id,
        "assigned_to": employee.employee_id,
    }


def update_task(user, task_id, status):
    role = _role(user)

    task = Task.objects.select_related(
        "assigned_to"
    ).filter(
        id=task_id
    ).first()

    if not task:
        return {
            "success": False,
            "error": "Task not found.",
        }

    if (
        role == "EMPLOYEE"
        and task.assigned_to_id != user.id
    ):
        return {
            "success": False,
            "error": (
                "You can only update your own tasks."
            ),
        }

    if (
        role == "MANAGER"
        and task.assigned_to.department_id
        != user.department_id
    ):
        return {
            "success": False,
            "error": "Outside your department.",
        }

    task.status = str(status).upper()
    task.save(update_fields=["status"])

    return {
        "success": True,
        "task_id": task.id,
        "status": task.status,
    }



def list_pending_leaves(user):
    role = _role(user)
    queryset = Leave.objects.filter(status="PENDING").select_related("employee", "employee__department")

    if role == "MANAGER":
        queryset = queryset.filter(employee__department_id=user.department_id)
    elif role not in {"HR", "ADMIN"}:
        return {"found": False, "message": "You are not authorized to view pending leave requests."}

    records = [
        {
            "id": leave.id,
            "employee_id": leave.employee.employee_id,
            "employee": _employee_name(leave.employee),
            "leave_type": leave.leave_type,
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "days": leave.days,
            "reason": leave.reason,
        }
        for leave in queryset.order_by("applied_at", "id")[:100]
    ]

    return {"found": True, "count": len(records), "records": records}

def get_policy(user, query="company policy"):
    words = [
        word.lower()
        for word in str(query).split()
        if len(word) > 2
    ][:10]

    scored = []

    for document in KnowledgeDocument.objects.all():
        text = " ".join(
            [
                str(document.title or ""),
                str(document.category or ""),
                str(document.content or ""),
            ]
        ).lower()

        score = sum(
            text.count(word)
            for word in words
        )

        if score:
            scored.append(
                (score, document)
            )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return {
        "query": query,
        "results": [
            {
                "title": document.title,
                "category": document.category,
                "content": document.content,
            }
            for _, document in scored[:5]
        ],
    }


def analyze_performance(user):
    start_date = timezone.localdate().replace(
        day=1
    )

    attendance = Attendance.objects.filter(
        employee=user,
        date__gte=start_date,
    )

    present = attendance.filter(
        status="PRESENT"
    ).count()

    absent = attendance.filter(
        status="ABSENT"
    ).count()

    miss_punch = attendance.filter(
        status="MISS_PUNCH"
    ).count()

    tasks = Task.objects.filter(
        assigned_to=user
    )

    total_tasks = tasks.count()

    completed_tasks = tasks.filter(
        status="DONE"
    ).count()

    attendance_total = (
        present
        + absent
        + miss_punch
    )

    attendance_percent = (
        round(
            (
                present
                + (0.5 * miss_punch)
            )
            / attendance_total
            * 100,
            1,
        )
        if attendance_total
        else 0
    )

    task_completion_percent = (
        round(
            completed_tasks
            / total_tasks
            * 100,
            1,
        )
        if total_tasks
        else 0
    )

    performance_score = round(
        attendance_percent * 0.6
        + task_completion_percent * 0.4,
        1,
    )

    return {
        "attendance_percent": attendance_percent,
        "task_completion_percent": (
            task_completion_percent
        ),
        "performance_score": performance_score,
        "present": present,
        "absent": absent,
        "miss_punch": miss_punch,
        "tasks_total": total_tasks,
        "tasks_done": completed_tasks,
    }


def team_performance(user):
    role = _role(user)

    employees = User.objects.filter(
        role="EMPLOYEE",
        is_active=True,
    )

    if role == "MANAGER":
        employees = employees.filter(
            department_id=user.department_id
        )

    return {
        "employees": [
            {
                "employee_id": employee.employee_id,
                "name": _employee_name(employee),
                **analyze_performance(employee),
            }
            for employee in employees.order_by(
                "employee_id"
            )
        ]
    }


def list_employees(user):
    employees = User.objects.filter(
        is_active=True,
        role="EMPLOYEE",
    )

    if _role(user) == "MANAGER":
        employees = employees.filter(
            department_id=user.department_id
        )

    employees = employees.select_related(
        "department",
        "manager",
    ).order_by(
        "employee_id"
    )[:200]

    return {
        "count": len(employees),
        "employees": [
            {
                "employee_id": employee.employee_id,
                "name": _employee_name(employee),
                "email": employee.email,
                "job_title": employee.job_title,
                "department": (
                    employee.department.name
                    if employee.department
                    else None
                ),
                "manager": (
                    _employee_name(employee.manager)
                    if employee.manager
                    else None
                ),
            }
            for employee in employees
        ],
    }


def get_employee(user, employee_id):
    employee = User.objects.select_related(
        "department"
    ).filter(
        employee_id=employee_id,
        is_active=True,
    ).first()

    if not employee:
        return {
            "found": False,
            "message": "Employee not found.",
        }

    if not _can_manage_employee(
        user,
        employee,
    ):
        return {
            "found": False,
            "message": (
                "You are not authorized to view "
                "this employee."
            ),
        }

    role = _role(user)

    return {
        "found": True,
        "employee_id": employee.employee_id,
        "name": _employee_name(employee),
        "email": employee.email,
        "phone": employee.phone,
        "job_title": employee.job_title,
        "role": employee.role,
        "department": (
            employee.department.name
            if employee.department
            else None
        ),
        "joining_date": (
            str(employee.joining_date)
            if employee.joining_date
            else None
        ),
        "salary": (
            str(employee.salary)
            if role in {
                "HR",
                "FINANCE",
                "ADMIN",
            }
            else "RESTRICTED"
        ),
    }


@transaction.atomic
def create_employee(
    user,
    name,
    email,
    password=None,
    role="EMPLOYEE",
    employee_id=None,
    department=None,
    salary="0",
    job_title="",
    phone="",
):
    if _role(user) not in {
        "HR",
        "ADMIN",
    }:
        return {
            "success": False,
            "error": "Not authorized.",
        }

    name = str(name or "").strip()
    email = str(email or "").strip().lower()

    if not name or not email:
        return {
            "success": False,
            "error": (
                "Name and email are required."
            ),
        }

    allowed_roles = {
        "EMPLOYEE",
        "MANAGER",
        "HR",
        "FINANCE",
    }

    role = str(role or "EMPLOYEE").upper()

    if role not in allowed_roles:
        return {
            "success": False,
            "error": "Invalid employee role.",
        }

    if User.objects.filter(
        email__iexact=email
    ).exists():
        return {
            "success": False,
            "error": "Email already exists.",
        }

    salary_value = _safe_decimal(
        salary
    )

    if salary_value is None:
        return {
            "success": False,
            "error": "Invalid salary.",
        }

    if salary_value < 0:
        return {
            "success": False,
            "error": (
                "Salary cannot be negative."
            ),
        }

    if employee_id:
        employee_id = str(employee_id).strip().upper()

        if User.objects.filter(
            employee_id=employee_id
        ).exists():
            return {
                "success": False,
                "error": (
                    "Employee ID already exists."
                ),
            }

    else:
        last_user = User.objects.order_by(
            "-id"
        ).first()

        next_number = (
            (last_user.id if last_user else 0)
            + 1001
        )

        employee_id = f"E{next_number}"

        while User.objects.filter(
            employee_id=employee_id
        ).exists():
            next_number += 1
            employee_id = f"E{next_number}"

    selected_department = None

    if department:
        selected_department = (
            Department.objects.filter(
                name__iexact=str(department).strip()
            ).first()
        )

        if not selected_department:
            return {
                "success": False,
                "error": "Department not found.",
            }

    name_parts = name.split()

    first_name = name_parts[0]
    last_name = " ".join(
        name_parts[1:]
    )

    temporary_password = (
        str(password)
        if password
        else _temporary_password()
    )

    employee = User(
        username=email,
        email=email,
        employee_id=employee_id,
        role=role,
        department=selected_department,
        salary=salary_value,
        job_title=str(job_title or "").strip(),
        phone=str(phone or "").strip(),
        first_name=first_name,
        last_name=last_name,
        must_change_password=True,
    )

    employee.set_password(
        temporary_password
    )

    employee.save()

    Notification.objects.create(
        employee=employee,
        title="Welcome to NovaHR",
        message=(
            f"Your login ID is {email}. "
            "Please change your password "
            "after your first login."
        ),
    )

    return {
        "success": True,
        "employee_id": employee.employee_id,
        "name": _employee_name(employee),
        "email": employee.email,
        "role": employee.role,
        "login_id": employee.email,
        "temporary_password": temporary_password,
        "must_change_password": True,
    }


@transaction.atomic
def update_employee(
    user,
    employee_id,
    **fields,
):
    if _role(user) not in {
        "HR",
        "ADMIN",
    }:
        return {
            "success": False,
            "error": "Not authorized.",
        }

    employee = User.objects.filter(
        employee_id=employee_id,
        is_active=True,
    ).first()

    if not employee:
        return {
            "success": False,
            "error": "Employee not found.",
        }

    if fields.get("email") is not None:
        new_email = str(
            fields["email"]
        ).strip().lower()

        if not new_email:
            return {
                "success": False,
                "error": (
                    "Email cannot be empty."
                ),
            }

        if User.objects.exclude(
            pk=employee.pk
        ).filter(
            email__iexact=new_email
        ).exists():
            return {
                "success": False,
                "error": "Email already exists.",
            }

        employee.email = new_email
        employee.username = new_email

    for field in (
        "phone",
        "job_title",
        "first_name",
        "last_name",
    ):
        if fields.get(field) is not None:
            setattr(
                employee,
                field,
                str(fields[field]).strip(),
            )

    if fields.get("salary") is not None:
        salary_value = _safe_decimal(
            fields["salary"]
        )

        if salary_value is None:
            return {
                "success": False,
                "error": "Invalid salary.",
            }

        if salary_value < 0:
            return {
                "success": False,
                "error": (
                    "Salary cannot be negative."
                ),
            }

        employee.salary = salary_value

    if fields.get("department") is not None:
        department = Department.objects.filter(
            name__iexact=str(
                fields["department"]
            ).strip()
        ).first()

        if not department:
            return {
                "success": False,
                "error": "Department not found.",
            }

        employee.department = department

    employee.save()

    return {
        "success": True,
        "employee_id": employee.employee_id,
        "message": "Employee updated.",
    }


@transaction.atomic
def delete_employee(user, employee_id):
    if _role(user) not in {
        "HR",
        "ADMIN",
    }:
        return {
            "success": False,
            "error": "Not authorized.",
        }

    employee = User.objects.filter(
        employee_id=employee_id,
        is_active=True,
    ).first()

    if not employee:
        return {
            "success": False,
            "error": "Employee not found.",
        }

    if employee.id == user.id:
        return {
            "success": False,
            "error": (
                "You cannot deactivate your own account."
            ),
        }

    employee.is_active = False

    employee.save(
        update_fields=["is_active"]
    )

    return {
        "success": True,
        "employee_id": employee.employee_id,
        "message": "Employee deactivated.",
    }


@transaction.atomic
def _decide(user, leave_id, decision):
    role = _role(user)

    if role not in {
        "MANAGER",
        "HR",
        "ADMIN",
    }:
        return {
            "success": False,
            "error": "Not authorized.",
        }

    leave = Leave.objects.select_related(
        "employee"
    ).filter(
        id=leave_id
    ).first()

    if not leave:
        return {
            "success": False,
            "error": "Leave request not found.",
        }

    if leave.status != "PENDING":
        return {
            "success": False,
            "error": (
                "Only pending leave requests "
                "can be processed."
            ),
        }

    if (
        role == "MANAGER"
        and leave.employee.department_id
        != user.department_id
    ):
        return {
            "success": False,
            "error": "Outside your department.",
        }

    leave.status = decision
    leave.approved_by = user
    leave.decision_at = timezone.now()

    leave.save(
        update_fields=[
            "status",
            "approved_by",
            "decision_at",
        ]
    )

    Notification.objects.create(
        employee=leave.employee,
        title=f"Leave {decision.lower()}",
        message=(
            f"Your leave request was "
            f"{decision.lower()}."
        ),
    )

    return {
        "success": True,
        "leave_id": leave.id,
        "status": decision,
    }


def approve_leave(user, leave_id):
    return _decide(
        user,
        leave_id,
        "APPROVED",
    )


def reject_leave(user, leave_id):
    return _decide(
        user,
        leave_id,
        "REJECTED",
    )


@transaction.atomic
def apply_leave(
    user,
    leave_type,
    start_date,
    end_date,
    reason,
):
    leave_type = str(
        leave_type or "CASUAL"
    ).upper()

    allowed_types = {
        "CASUAL",
        "SICK",
        "ANNUAL",
    }

    if leave_type not in allowed_types:
        leave_type = "CASUAL"

    try:
        parsed_start = date.fromisoformat(str(start_date))
        parsed_end = date.fromisoformat(str(end_date))
    except ValueError:
        return {
            "success": False,
            "error": "Invalid date format. Use YYYY-MM-DD.",
        }

    if parsed_end < parsed_start:
        return {
            "success": False,
            "error": "End date cannot be before start date.",
        }

    leave = Leave.objects.create(
        employee=user,
        leave_type=leave_type,
        start_date=parsed_start,
        end_date=parsed_end,
        reason=str(reason or "").strip(),
        status="PENDING",
    )

    return {
        "success": True,
        "leave_id": leave.id,
        "status": leave.status,
        "days": leave.days,
    }


def cancel_leave(user, leave_id):
    leave = Leave.objects.filter(
        id=leave_id,
        employee=user,
    ).first()

    if not leave:
        return {
            "success": False,
            "error": "Leave request not found.",
        }

    if leave.status != "PENDING":
        return {
            "success": False,
            "error": "Only pending leave requests can be cancelled.",
        }

    leave.status = "CANCELLED"
    leave.save(update_fields=["status"])

    return {
        "success": True,
        "leave_id": leave.id,
        "status": "CANCELLED",
    }


def explain_salary_change(user):
    payrolls = Payroll.objects.filter(
        employee=user
    ).order_by("-year", "-month")[:2]

    if len(payrolls) < 2:
        return {
            "found": False,
            "message": "Insufficient payroll history to analyze salary change.",
        }

    current, previous = payrolls[0], payrolls[1]
    diff = current.final_salary - previous.final_salary

    reasons = []
    if current.bonus != previous.bonus:
        reasons.append(f"Bonus changed by ₹{current.bonus - previous.bonus}")
    if current.deductions != previous.deductions:
        reasons.append(f"Deductions changed by ₹{current.deductions - previous.deductions}")
    if current.base_salary != previous.base_salary:
        reasons.append(f"Base salary revised by ₹{current.base_salary - previous.base_salary}")

    if not reasons:
        reasons.append("Variation due to working/attendance day adjustments")

    return {
        "found": True,
        "previous_salary": str(previous.final_salary),
        "previous_period": f"{previous.month}/{previous.year}",
        "current_salary": str(current.final_salary),
        "current_period": f"{current.month}/{current.year}",
        "difference": str(diff),
        "reasons": reasons,
    }


def send_notification(user, employee_id, title, message):
    if _role(user) not in {"MANAGER", "HR", "ADMIN"}:
        return {
            "success": False,
            "error": "Not authorized.",
        }

    target = User.objects.filter(
        employee_id=employee_id,
        is_active=True,
    ).first()

    if not target:
        return {
            "success": False,
            "error": "Employee not found.",
        }

    notification = Notification.objects.create(
        employee=target,
        title=str(title).strip(),
        message=str(message).strip(),
    )

    return {
        "success": True,
        "notification_id": notification.id,
        "employee_id": target.employee_id,
    }


def get_notifications(user):
    notifications = Notification.objects.filter(
        employee=user
    ).order_by("-created_at")[:50]

    unread_count = notifications.filter(is_read=False).count()

    return {
        "count": unread_count,
        "notifications": [
            {
                "id": notif.id,
                "title": notif.title,
                "message": notif.message,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat(),
            }
            for notif in notifications
        ],
    }


def mark_notifications_read(user):
    updated = Notification.objects.filter(
        employee=user,
        is_read=False,
    ).update(is_read=True)

    return {
        "success": True,
        "marked_read_count": updated,
    }


def profile(user):
    return {
        "found": True,
        "employee_id": user.employee_id,
        "name": _employee_name(user),
        "email": user.email,
        "role": user.role,
        "job_title": user.job_title,
        "phone": user.phone,
        "department": (
            user.department.name if user.department else None
        ),
        "joining_date": (
            str(user.joining_date) if user.joining_date else None
        ),
    }


def department_summary(user):
    if _role(user) not in {"MANAGER", "HR", "ADMIN"}:
        return {
            "found": False,
            "message": "Not authorized.",
        }

    dept = user.department
    if not dept and _role(user) == "MANAGER":
        return {
            "found": False,
            "message": "No department assigned to manager.",
        }

    employees = (
        User.objects.filter(department=dept, is_active=True)
        if dept
        else User.objects.filter(is_active=True)
    )

    return {
        "found": True,
        "department_name": dept.name if dept else "All Departments",
        "total_employees": employees.count(),
        "managers": employees.filter(role="MANAGER").count(),
    }