from django.db.models import Count
from core.models import Attendance, User

def summary():
 qs=Attendance.objects.values('status').annotate(count=Count('id'))
 return {x['status']:x['count'] for x in qs}

def analytics():
 data=summary(); total=sum(data.values()); present=data.get('PRESENT',0); absent=data.get('ABSENT',0); miss=data.get('MISS_PUNCH',0)
 return {'total_records':total,'present':present,'absent':absent,'miss_punch':miss,'attendance_rate':round((present/total*100),2) if total else 0}

def low_attendance_employees(threshold=75):
 rows=[]
 for u in User.objects.filter(is_active=True,role='EMPLOYEE'):
  q=Attendance.objects.filter(employee=u); total=q.count(); present=q.filter(status='PRESENT').count(); rate=round(present/total*100,2) if total else 0
  if total and rate<threshold: rows.append({'employee_id':u.employee_id,'name':u.get_full_name() or u.username,'attendance_rate':rate,'records':total})
 return sorted(rows,key=lambda x:x['attendance_rate'])
