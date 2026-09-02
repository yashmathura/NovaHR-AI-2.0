from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name


class Department(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments")
    def __str__(self): return self.name


class Team(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="teams")
    leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="leading_teams")
    def __str__(self): return self.name


class User(AbstractUser):
    ROLE_CHOICES = [(x, x.title()) for x in ("ADMIN", "HR", "MANAGER", "FINANCE", "EMPLOYEE")]
    employee_id = models.CharField(max_length=100, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="EMPLOYEE")
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    annual_leave_quota = models.PositiveIntegerField(default=24)
    casual_leave_quota = models.PositiveIntegerField(default=12)
    sick_leave_quota = models.PositiveIntegerField(default=10)
    must_change_password = models.BooleanField(default=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="members")
    manager = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="direct_reports")
    last_salary_revision = models.DateField(null=True, blank=True)
    def __str__(self): return f"{self.get_full_name() or self.username} ({self.employee_id})"


class Attendance(models.Model):
    STATUS = [("PRESENT", "Present"), ("ABSENT", "Absent"), ("MISS_PUNCH", "Miss Punch")]
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(default=timezone.localdate)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PRESENT")
    source = models.CharField(max_length=50, default="WEB")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["employee", "date"], name="unique_employee_attendance_day")]
        ordering = ["-date"]
    @property
    def hours_worked(self):
        if self.check_in and self.check_out:
            return round((self.check_out - self.check_in).total_seconds() / 3600, 2)
        return 0


class Leave(models.Model):
    TYPES = [("CASUAL", "Casual"), ("SICK", "Sick"), ("ANNUAL", "Annual")]
    STATUS = [
    ("PENDING", "Pending"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
    ("CANCELLED", "Cancelled"),
]
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=20, choices=TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_leaves")
    applied_at = models.DateTimeField(auto_now_add=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    @property
    def days(self): return (self.end_date - self.start_date).days + 1


class Payroll(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payrolls")
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    working_days = models.PositiveSmallIntegerField(default=22)
    present_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    absent_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["employee", "month", "year"], name="unique_employee_payroll_period")]
    def calculate(self):
        per_day = self.base_salary / Decimal(str(self.working_days or 22))
        self.deductions = (per_day * self.absent_days).quantize(Decimal("0.01"))
        self.final_salary = (self.base_salary - self.deductions + self.bonus).quantize(Decimal("0.01"))
    def save(self, *args, **kwargs):
        self.calculate(); super().save(*args, **kwargs)


class Task(models.Model):
    STATUS = [("TODO", "To Do"), ("IN_PROGRESS", "In Progress"), ("DONE", "Done")]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_tasks")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_tasks")
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, default="MEDIUM")
    status = models.CharField(max_length=20, choices=STATUS, default="TODO")
    created_at = models.DateTimeField(auto_now_add=True)


class KnowledgeDocument(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=80, default="POLICY")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title


class Notification(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class AgentAuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    tool_name = models.CharField(max_length=100)
    arguments = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.tool_name} - {self.created_at:%Y-%m-%d %H:%M}"


class AIConversation(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='ai_conversations')
    title=models.CharField(max_length=200,default='NovaHR conversation')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-updated_at']

class AIMessage(models.Model):
    conversation=models.ForeignKey(AIConversation,on_delete=models.CASCADE,related_name='messages')
    role=models.CharField(max_length=20)
    content=models.TextField()
    metadata=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['created_at']

class DocumentChunk(models.Model):
    document=models.ForeignKey(KnowledgeDocument,on_delete=models.CASCADE,related_name='chunks')
    content=models.TextField()
    chunk_index=models.PositiveIntegerField()
    embedding=models.JSONField(default=list,blank=True)
    metadata=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['document','chunk_index'],name='unique_document_chunk')]

class AIInsight(models.Model):
    category=models.CharField(max_length=80)
    title=models.CharField(max_length=200)
    content=models.TextField()
    data=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class AIQueryFeedback(models.Model):
    message=models.ForeignKey(AIMessage,on_delete=models.CASCADE,related_name='feedback_items')
    rating=models.PositiveSmallIntegerField(default=3)
    feedback=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
