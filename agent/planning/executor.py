from agent.analytics.attendance import analytics as attendance_analytics, low_attendance_employees
from agent.analytics.payroll import analytics as payroll_analytics
from core.models import Task

def execute_plan(steps):
 ctx={}
 for step in steps:
  if step.intent=='analytics_attendance': ctx['attendance']=attendance_analytics()
  elif step.intent=='analytics_low_attendance': ctx['low_attendance']=low_attendance_employees()
  elif step.intent=='analytics_pending_tasks': ctx['pending_tasks']=list(Task.objects.exclude(status='DONE').values('assigned_to__employee_id','assigned_to__first_name','assigned_to__last_name','title','status'))
  elif step.intent=='analytics_payroll': ctx['payroll']=payroll_analytics()
  elif step.intent=='combine_low_attendance_tasks':
   ids={x['employee_id'] for x in ctx.get('low_attendance',[])}
   matches=[]
   for task in ctx.get('pending_tasks',[]):
    if task['assigned_to__employee_id'] in ids: matches.append(task)
   ctx['matches']=matches
 return ctx
