from .schemas import PlanStep

def plan(message,intent=None):
 t=(message or '').lower()
 if ('low attendance' in t or 'attendance problem' in t) and ('task' in t or 'pending' in t):
  return [PlanStep('attendance','analytics_low_attendance',{}),PlanStep('tasks','analytics_pending_tasks',{}),PlanStep('combine','combine_low_attendance_tasks',{})]
 if 'payroll' in t and any(x in t for x in ('trend','analytics','summary','analyze')): return [PlanStep('payroll','analytics_payroll',{})]
 if 'attendance' in t and any(x in t for x in ('trend','analytics','summary','analyze')): return [PlanStep('attendance','analytics_attendance',{})]
 return [PlanStep('single',intent or 'unknown',{})]
