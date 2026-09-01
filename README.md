# NovaHR Agent v3 — Independent Multi-Role HR ERP

NovaHR is a Django + PostgreSQL HR/Payroll ERP with an independent, deterministic agent. **Gemini and OpenAI are not required and are not called by the agent.**

## Included roles
- **Employee:** leave balance/application/cancellation, attendance, salary/payslip, tasks, policies, performance, profile and notifications.
- **Manager:** department employees, team attendance, team performance, task assignment, leave approval/rejection and notifications.
- **HR:** employee onboarding/update/deactivation, leave management, attendance, payroll/reporting, policies, tasks and notifications.
- **Finance:** payroll generation, payroll reports, permitted payroll/attendance views and policy access.
- **Admin:** full operational access.

## Agent architecture
`User -> Local Intent Router -> RBAC -> Planner -> Secure ORM Tool -> PostgreSQL -> Audit Log -> Response`

Every agent action is checked against a role permission matrix and written to `AgentAuditLog`.

## Demo accounts
- Admin: `admin` / `Admin@12345`
- HR: `hr` / `Hr@12345`
- Manager: `manager` / `Manager@12345`
- Finance: `finance` / `Finance@12345`
- Employee: `employee` / `Employee@12345`
- Employee 2: `employee2` / `Employee@12345`
- Employee 3: `employee3` / `Employee@12345`

Run:
```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/` and use **Agent AI**.

## Agent examples
- `How many leaves do I have left?`
- `Check in today`
- `Show my salary`
- `Who is absent today?`
- `Show team performance`
- `assign task to E1005 title: Prepare report, due_date: 2026-09-01, priority: HIGH`
- `approve leave 1`
- `add employee name: Rahul Kumar, email: rahul@example.com, salary: 45000, department: Engineering, job_title: Developer`
- `update employee E1005 salary: 50000, job_title: Senior Developer`
- `deactivate employee E1005`
- `generate payroll`
- `show payroll report`

The agent intentionally uses local rules for predictable, explainable and API-free operation. An LLM can be plugged in later without replacing the ERP tools or RBAC layer.


## NovaLM — Custom Local Language Model

NovaHR includes **NovaLM-1**, a compact Transformer language-understanding model trained from scratch on an HR-domain intent corpus. It is not a hosted Gemini/OpenAI wrapper and uses no external inference API.

Train it locally after installing requirements:

```powershell
python manage.py train_novalm --epochs 18
```

The trained checkpoint is stored under `agent/models/`. The agent uses NovaLM when confidence is high and falls back to the deterministic router when confidence is low, preserving predictable security behavior.

### New employee identity

When HR/Admin creates an employee, the employee's **email address becomes the permanent login ID/username**. If the password field is left blank, NovaHR generates a secure temporary password and displays it once after creation. The separate HR employee ID (E100x) remains available for payroll/attendance records.
