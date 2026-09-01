import secrets
import string

from core.models import User


def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits + "@#$%"

    while True:
        password = "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
        ):
            return password


def admin_reset_password(admin, employee_id, new_password=None):
    if admin.role != "ADMIN":
        return {
            "success": False,
            "error": "Only System Admin can reset employee passwords."
        }

    employee = User.objects.filter(
        employee_id=employee_id,
        is_active=True
    ).first()

    if not employee:
        return {
            "success": False,
            "error": "Employee not found."
        }

    password = new_password or generate_password()

    employee.set_password(password)
    employee.must_change_password = True
    employee.save(update_fields=[
        "password",
        "must_change_password"
    ])

    return {
        "success": True,
        "employee_id": employee.employee_id,
        "name": employee.get_full_name() or employee.username,
        "temporary_password": password,
        "must_change_password": True,
        "message": "Password reset successfully. Employee must change it after login."
    }