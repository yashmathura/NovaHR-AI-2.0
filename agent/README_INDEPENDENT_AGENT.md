# NovaHR Independent Multi-Role Agent

NovaHR is an independent deterministic agent. It does not call Gemini or OpenAI during normal operation.

## Agent flow
User -> Local Intent Router -> RBAC -> Planner -> Secure Django ORM Tool -> PostgreSQL -> Audited Result

## Roles
- EMPLOYEE: personal attendance, leave, payroll, tasks, profile, notifications, policies and performance.
- MANAGER: employee scope for their department, team attendance/performance, task assignment, leave decisions and notifications.
- HR: employee onboarding/updates/deactivation, leave decisions, attendance, payroll/reporting, policies, tasks and notifications.
- FINANCE: payroll generation/reporting and permitted financial/ERP views; no employee-management actions.
- ADMIN: full operational access.

## Examples
- `How many leaves do I have left?`
- `Check in today`
- `Show my salary`
- `Who is absent today?` (Manager/HR/Admin)
- `Show team performance` (Manager/HR/Admin)
- `assign task to E1005 title: Prepare report, due_date: 2026-09-01, priority: HIGH`
- `approve leave 3`
- `add employee name: Rahul Kumar, email: rahul@example.com, salary: 45000, department: Engineering, job_title: Developer`
- `update employee E1005 salary: 50000, job_title: Senior Developer`
- `deactivate employee E1005`
- `generate payroll`
- `show payroll report`

The natural-language layer is intentionally local/rule-based for predictable security and zero model/API dependency. A local LLM can be added later without changing the ERP tools.

## NovaLM-1 (Custom Transformer)

NovaHR now contains a custom local language-understanding model called **NovaLM-1**.
It is a compact Transformer encoder trained **from scratch** on a generated NovaHR HR-domain corpus covering 28 intents. No Gemini/OpenAI endpoint or pretrained language model is required for inference.

### Train

```powershell
python manage.py train_novalm --epochs 18
```

Training creates:

- `agent/models/novalm_intent.pt` — learned model weights
- `agent/models/novalm_meta.json` — vocabulary and intent metadata

### Inference safety

The agent uses NovaLM when its confidence is at least 0.58. Otherwise it falls back to the deterministic regex router. This hybrid design makes the system both adaptive to natural language and predictable for RBAC/security-sensitive actions.
