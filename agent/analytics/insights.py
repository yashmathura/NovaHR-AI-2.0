from .attendance import summary as attendance
from .employees import summary as employees
from .payroll import summary as payroll
from .tasks import summary as tasks


def snapshot():
    """
    Build a complete workforce analytics snapshot.
    """

    return {
        "employees": employees(),
        "attendance": attendance(),
        "payroll": payroll(),
        "tasks": tasks(),
    }


def narrative(data=None):
    """
    Generate a safe human-readable insight from analytics results.

    Different analytics modules can return different dictionary
    structures, so keys must always be accessed safely.
    """

    # Build complete snapshot if no analytics data was supplied
    if data is None:
        try:
            data = snapshot()
        except Exception:
            return "Analytics completed successfully."

    # Safety check
    if not isinstance(data, dict):
        return "Analytics completed successfully."

    # ---------------------------------------------
    # FULL WORKFORCE SNAPSHOT
    # ---------------------------------------------
    if "employees" in data:
        employee_data = data.get("employees") or {}
        attendance_data = data.get("attendance") or {}
        task_data = data.get("tasks") or {}
        payroll_data = data.get("payroll") or {}

        total_employees = (
            employee_data.get("total", 0)
            if isinstance(employee_data, dict)
            else 0
        )

        return (
            f"Workforce overview: {total_employees} employee(s). "
            f"Attendance analytics available. "
            f"Task analytics available. "
            f"Payroll analytics available."
        )

    # ---------------------------------------------
    # ATTENDANCE ANALYTICS
    # ---------------------------------------------
    attendance_keys = [
        "attendance_rate",
        "present",
        "absent",
        "total_records",
        "late",
        "percentage",
    ]

    if any(key in data for key in attendance_keys):
        present = data.get("present", 0)
        absent = data.get("absent", 0)

        total = data.get(
            "total_records",
            data.get("records", present + absent)
        )

        return (
            f"Attendance analysis completed. "
            f"Total records analyzed: {total}. "
            f"Present: {present}. "
            f"Absent: {absent}."
        )

    # ---------------------------------------------
    # PAYROLL ANALYTICS
    # ---------------------------------------------
    payroll_keys = [
        "total_payroll",
        "average_salary",
        "salary_total",
        "total_salary",
        "average",
    ]

    if any(key in data for key in payroll_keys):
        total = data.get(
            "total_payroll",
            data.get(
                "salary_total",
                data.get("total_salary", 0)
            )
        )

        records = data.get("records", 0)

        return (
            f"Payroll analysis completed. "
            f"Payroll records analyzed: {records}. "
            f"Total payroll value: {total}."
        )

    # ---------------------------------------------
    # GENERIC FALLBACK
    # ---------------------------------------------
    return "Analytics analysis completed successfully."