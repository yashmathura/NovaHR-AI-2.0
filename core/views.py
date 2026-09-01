from calendar import monthrange
from datetime import date
from decimal import Decimal
import secrets
import string
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.pdfgen import canvas
from .models import User, Attendance, Leave, Payroll, Task, KnowledgeDocument, Notification


def roles(*allowed):
    def deco(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated: return redirect("login")
            if request.user.role not in allowed: return HttpResponseForbidden("Access denied")
            return fn(request, *args, **kwargs)
        return wrapper
    return deco


def login_view(request):
    if request.user.is_authenticated: return redirect("dashboard")
    error = None
    if request.method == "POST":
        login_id = (request.POST.get("username") or request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        # Employee login ID is their email; legacy demo accounts can still use username.
        user = authenticate(request, username=login_id, password=password)
        if not user:
            user = User.objects.filter(email__iexact=login_id, is_active=True).first()
            if user and user.check_password(password):
                login(request, user)
            else:
                user = None
        if user: login(request, user); return redirect("dashboard")
        error = "Invalid email/username or password."
    return render(request, "login.html", {"error": error})

@login_required
def logout_view(request): logout(request); return redirect("login")

@login_required
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    scope = Attendance.objects.all() if user.role in ("ADMIN","HR","FINANCE") else Attendance.objects.filter(employee=user)
    if user.role == "MANAGER": scope = scope.filter(employee__department=user.department)
    employees = User.objects.filter(role="EMPLOYEE")
    if user.role == "MANAGER": employees = employees.filter(department=user.department)
    context = {
        "user": user, "today": today, "employees_count": employees.count(),
        "present_today": scope.filter(date=today, status="PRESENT").count(),
        "pending_leaves": Leave.objects.filter(status="PENDING", **({} if user.role != "MANAGER" else {"employee__department":user.department})).count(),
        "payroll_total": Payroll.objects.filter(employee__in=employees, month=today.month, year=today.year).aggregate(total=Sum("final_salary"))["total"] or 0,
        "my_leaves": Leave.objects.filter(employee=user).order_by("-applied_at")[:5],
        "my_tasks": Task.objects.filter(assigned_to=user).order_by("status","due_date")[:6],
        "recent_attendance": scope.order_by("-date")[:8],
        "notifications": Notification.objects.filter(employee=user, read=False)[:5],
    }
    return render(request, "dashboard.html", context)

def _generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + "@#$%"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password):
            return password

def employee_create(request):
    if request.user.role not in ("ADMIN", "HR"): return HttpResponseForbidden("Access denied")
    if request.method != "POST": return redirect("employees")
    name=request.POST.get("name"," ").strip(); email=request.POST.get("email","").strip().lower()
    if not name or not email: return HttpResponseForbidden("Name and email are required")
    if User.objects.filter(email__iexact=email).exists(): return HttpResponseForbidden("Email already exists")
    dept=get_object_or_404(__import__("core.models",fromlist=["Department"]).Department,id=request.POST.get("department_id")) if request.POST.get("department_id") else None
    first,*rest=name.split(); password=request.POST.get("password","").strip() or _generate_temp_password()
    # Email is the permanent login ID. employee_id remains a separate HR identifier.
    employee_id=request.POST.get("employee_id","").strip() or f"E{User.objects.count()+1001}"
    if User.objects.filter(employee_id=employee_id).exists(): return HttpResponseForbidden("Employee ID already exists")
    u=User(username=email,email=email,employee_id=employee_id,role="EMPLOYEE",department=dept,salary=Decimal(request.POST.get("salary") or "0"),job_title=request.POST.get("job_title",""),phone=request.POST.get("phone",""),first_name=first,last_name=" ".join(rest),joining_date=date.today(),must_change_password=True)
    u.set_password(password); u.save(); Notification.objects.create(employee=u,title="Welcome to NovaHR",message=f"Your login ID is your email address: {email}. Temporary password: {password}. Please change it after first login.")
    request.session["new_employee_credentials"]={"email":email,"password":password,"employee_id":employee_id,"name":name}
    return redirect("employees")
@login_required
def employee_reset_password(request, employee_id):
    if request.user.role != "ADMIN":
        return HttpResponseForbidden("Only Admin can reset employee passwords.")

    if request.method != "POST":
        return redirect("employees")

    employee = get_object_or_404(
        User,
        employee_id=employee_id,
        role="EMPLOYEE",
        is_active=True
    )

    password = request.POST.get("password", "").strip()

    if not password:
        password = _generate_temp_password()

    if len(password) < 8:
        return HttpResponseForbidden("Password must be at least 8 characters long.")

    employee.set_password(password)
    employee.must_change_password = True
    employee.save(update_fields=["password", "must_change_password"])

    Notification.objects.create(
        employee=employee,
        title="Password Reset",
        message=f"Your NovaHR password has been reset. Temporary password: {password}"
    )

    request.session["reset_credentials"] = {
        "email": employee.email,
        "password": password,
        "employee_id": employee.employee_id,
        "name": employee.get_full_name() or employee.username,
    }

    return redirect("employees")
@login_required
def employees(request):
    if request.user.role not in ("ADMIN", "HR", "MANAGER"):
        return HttpResponseForbidden("Access denied")

    qs = User.objects.filter(
        role="EMPLOYEE"
    ).select_related("department", "manager")

    if request.user.role == "MANAGER":
        qs = qs.filter(department=request.user.department)

    from .models import Department

    departments = Department.objects.all().order_by("name")

    return render(
        request,
        "employees.html",
        {
            "employees": qs,
            "departments": departments,
            "new_credentials": request.session.pop(
                "new_employee_credentials",
                None
            ),
            "reset_credentials": request.session.pop(
                "reset_credentials",
                None
            ),
        }
    )

@login_required
def attendance(request):
    today = timezone.localdate(); user = request.user
    if request.method == "POST":
        action = request.POST.get("action")
        rec, _ = Attendance.objects.get_or_create(employee=user, date=today)
        now = timezone.now()
        if action == "check_in" and not rec.check_in: rec.check_in=now; rec.status="PRESENT"; rec.source="WEB"; rec.save()
        elif action == "check_out" and rec.check_in and not rec.check_out: rec.check_out=now; rec.save()
        return redirect("attendance")
    records = Attendance.objects.filter(employee=user) if user.role == "EMPLOYEE" else Attendance.objects.select_related("employee")[:100]
    return render(request, "attendance.html", {"records": records, "today_record": Attendance.objects.filter(employee=user,date=today).first()})

@login_required
def leave_page(request):
    user = request.user
    if request.method == "POST":
        Leave.objects.create(employee=user, leave_type=request.POST["leave_type"], start_date=request.POST["start_date"], end_date=request.POST["end_date"], reason=request.POST["reason"])
        Notification.objects.create(employee=user, title="Leave submitted", message="Your leave request has been submitted for approval.")
        return redirect("leave_page")
    qs = Leave.objects.select_related("employee").order_by("-applied_at")
    if user.role == "EMPLOYEE": qs = qs.filter(employee=user)
    elif user.role == "MANAGER": qs = qs.filter(employee__department=user.department)
    return render(request, "leave.html", {"leaves": qs, "can_decide": user.role in ("ADMIN","HR","MANAGER")})

@login_required
def leave_decision(request, leave_id):
    if request.user.role not in ("ADMIN","HR","MANAGER"): return HttpResponseForbidden("Access denied")
    leave = get_object_or_404(Leave, id=leave_id)
    if request.user.role == "MANAGER" and leave.employee.department_id != request.user.department_id: return HttpResponseForbidden("Access denied")
    decision = request.POST.get("decision")
    if decision in ("APPROVED","REJECTED"):
        leave.status=decision; leave.approved_by=request.user; leave.decision_at=timezone.now(); leave.save()
        Notification.objects.create(employee=leave.employee, title=f"Leave {decision.lower()}", message=f"Your {leave.leave_type.lower()} leave request was {decision.lower()}.")
    return redirect("leave_page")

@roles("ADMIN","HR","FINANCE")
def payroll_page(request):
    today=timezone.localdate()
    if request.method == "POST":
        emp=get_object_or_404(User,id=request.POST["employee_id"],role="EMPLOYEE")
        month=int(request.POST.get("month",today.month)); year=int(request.POST.get("year",today.year))
        records=Attendance.objects.filter(employee=emp,date__year=year,date__month=month)
        present=records.filter(status="PRESENT").count(); absent=records.filter(status="ABSENT").count()
        approved=Leave.objects.filter(employee=emp,status="APPROVED",start_date__year=year,start_date__month=month).count()
        Payroll.objects.update_or_create(employee=emp,month=month,year=year,defaults={"base_salary":emp.salary,"working_days":22,"present_days":present,"absent_days":absent,"leave_days":approved})
        return redirect("payroll")
    employees=User.objects.filter(role="EMPLOYEE")
    payslips=Payroll.objects.select_related("employee").order_by("-year","-month")[:50]
    return render(request,"payroll.html",{"employees":employees,"payslips":payslips,"today":today})

@login_required
def payslip(request,payroll_id):
    p=get_object_or_404(Payroll, id=payroll_id)
    if request.user.role=="EMPLOYEE" and p.employee_id != request.user.id: return HttpResponseForbidden("Access denied")
    response=__import__('django').http.HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="payslip-{p.employee.employee_id}-{p.month}-{p.year}.pdf"'
    c=canvas.Canvas(response); c.setFont("Helvetica-Bold",18); c.drawString(60,790,"NovaTech Solutions — Payslip")
    lines=[f"Employee: {p.employee.get_full_name()}",f"Employee ID: {p.employee.employee_id}",f"Period: {p.month}/{p.year}",f"Base Salary: ₹{p.base_salary}",f"Present Days: {p.present_days}",f"Absent Days: {p.absent_days}",f"Deductions: ₹{p.deductions}",f"Bonus: ₹{p.bonus}",f"Net Salary: ₹{p.final_salary}"]
    y=740
    for line in lines: c.setFont("Helvetica",11); c.drawString(70,y,line); y-=28
    c.showPage(); c.save(); return response

@login_required
def tasks_page(request):
    user=request.user
    if request.method=="POST" and user.role in ("ADMIN","MANAGER"):
        assigned=get_object_or_404(User,id=request.POST["assigned_to"],role="EMPLOYEE")
        if user.role=="MANAGER" and assigned.department_id != user.department_id: return HttpResponseForbidden("Access denied")
        Task.objects.create(title=request.POST["title"],description=request.POST.get("description",""),assigned_to=assigned,assigned_by=user,due_date=request.POST.get("due_date") or None,priority=request.POST.get("priority","MEDIUM"))
        return redirect("tasks")
    qs=Task.objects.select_related("assigned_to","assigned_by")
    if user.role=="EMPLOYEE": qs=qs.filter(assigned_to=user)
    elif user.role=="MANAGER": qs=qs.filter(assigned_to__department=user.department)
    return render(request,"tasks.html",{"tasks":qs,"employees":User.objects.filter(role="EMPLOYEE")})

@login_required
def knowledge(request):
    docs=KnowledgeDocument.objects.all().order_by("category","title")
    return render(request,"knowledge.html",{"docs":docs})
