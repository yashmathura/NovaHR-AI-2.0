from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("employees/", views.employees, name="employees"),
    path("employees/create/", views.employee_create, name="employee_create"),
    path("employees/<str:employee_id>/reset-password/", views.employee_reset_password, name="employee_reset_password"),
    path("attendance/", views.attendance, name="attendance"),
    path("leave/", views.leave_page, name="leave_page"),
    path("leave/<int:leave_id>/decision/", views.leave_decision, name="leave_decision"),
    path("payroll/", views.payroll_page, name="payroll"),
    path("payroll/<int:payroll_id>/payslip/", views.payslip, name="payslip"),
    path("tasks/", views.tasks_page, name="tasks"),
    path("knowledge/", views.knowledge, name="knowledge"),
]
