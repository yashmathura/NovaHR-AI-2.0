from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Company, Department, Team, Attendance, Leave, Payroll, Task, KnowledgeDocument, Notification
User=get_user_model()

class Command(BaseCommand):
    help="Create a complete NovaHR demo dataset for all roles"
    def handle(self,*args,**kwargs):
        company,_=Company.objects.get_or_create(name="NovaTech Solutions",defaults={"email":"hr@novatech.example"})
        eng,_=Department.objects.get_or_create(name="Engineering",company=company)
        finance_dept,_=Department.objects.get_or_create(name="Finance",company=company)
        hr_dept,_=Department.objects.get_or_create(name="Human Resources",company=company)
        admin=self.user("admin","Admin@12345","ADMIN","E1001","System Admin",90000,eng)
        hr=self.user("hr","Hr@12345","HR","E1002","Priya Sharma",75000,hr_dept)
        manager=self.user("manager","Manager@12345","MANAGER","E1003","Arjun Mehta",95000,eng)
        fin=self.user("finance","Finance@12345","FINANCE","E1004","Neha Verma",80000,finance_dept)
        e1=self.user("employee","Employee@12345","EMPLOYEE","E1005","Riya Sharma",55000,eng)
        e2=self.user("employee2","Employee@12345","EMPLOYEE","E1007","Aman Gupta",48000,eng)
        e3=self.user("employee3","Employee@12345","EMPLOYEE","E1008","Sneha Singh",62000,eng)
        team,_=Team.objects.get_or_create(name="Platform Team",department=eng,defaults={"leader":manager}); team.leader=manager; team.save()
        for e in (e1,e2,e3): e.team=team; e.manager=manager; e.save()
        today=date.today()
        for e in (e1,e2,e3):
            for i in range(1,16):
                d=today-timedelta(days=i)
                Attendance.objects.get_or_create(employee=e,date=d,defaults={"status":"ABSENT" if i in (5,11) and e==e2 else "PRESENT"})
            Payroll.objects.update_or_create(employee=e,month=today.month,year=today.year,defaults={"base_salary":e.salary,"working_days":22,"present_days":18,"absent_days":2,"leave_days":2})
        Leave.objects.get_or_create(employee=e1,leave_type="CASUAL",start_date=today+timedelta(days=10),end_date=today+timedelta(days=12),defaults={"reason":"Family function","status":"PENDING"})
        Leave.objects.get_or_create(employee=e2,leave_type="SICK",start_date=today-timedelta(days=3),end_date=today-timedelta(days=2),defaults={"reason":"Medical rest","status":"APPROVED","approved_by":hr})
        Task.objects.get_or_create(title="Complete payroll review",assigned_to=e1,defaults={"assigned_by":manager,"due_date":today+timedelta(days=4),"priority":"HIGH"})
        Task.objects.get_or_create(title="Prepare API documentation",assigned_to=e2,defaults={"assigned_by":manager,"due_date":today+timedelta(days=7),"priority":"MEDIUM"})
        Task.objects.get_or_create(title="Finish dashboard QA",assigned_to=e3,defaults={"assigned_by":manager,"due_date":today+timedelta(days=2),"priority":"HIGH","status":"DONE"})
        KnowledgeDocument.objects.get_or_create(title="Leave Policy",defaults={"category":"LEAVE","content":"Employees receive 12 casual, 10 sick and 24 annual leave days per year. Leave must be applied before the start date when possible. Manager or HR approval is required. Overlapping leave is not allowed."})
        KnowledgeDocument.objects.get_or_create(title="Payroll Policy",defaults={"category":"PAYROLL","content":"Monthly payroll is based on base salary, working days, attendance deductions, approved leave and bonuses. Payslips are available after payroll generation."})
        KnowledgeDocument.objects.get_or_create(title="Attendance Policy",defaults={"category":"ATTENDANCE","content":"Employees should check in by 9:30 AM and check out at the end of their workday. Missing punches should be reported to HR."})
        Notification.objects.get_or_create(employee=e1,title="Welcome to NovaHR",defaults={"message":"Your employee workspace is ready."})
        self.stdout.write(self.style.SUCCESS("NovaHR demo data created for Admin, HR, Manager, Finance and 3 Employees."))
    def user(self,username,password,role,employee_id,full_name,salary,dept):
        u,_=User.objects.get_or_create(username=username,defaults={"employee_id":employee_id,"role":role,"salary":salary,"department":dept})
        u.employee_id=employee_id; u.role=role; u.salary=salary; u.department=dept; u.joining_date=u.joining_date or date.today(); u.first_name,*rest=full_name.split(); u.last_name=" ".join(rest); u.set_password(password); u.save(); return u
