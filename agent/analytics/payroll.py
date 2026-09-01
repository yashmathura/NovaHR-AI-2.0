from django.db.models import Sum
from core.models import Payroll

def summary(): return {'records':Payroll.objects.count(),'total_net':str(Payroll.objects.aggregate(v=Sum('final_salary'))['v'] or 0)}
def analytics():
 rows=[]
 for p in Payroll.objects.order_by('year','month'):
  rows.append({'period':f'{p.month:02d}/{p.year}','net':float(p.final_salary),'deductions':float(p.deductions),'bonus':float(p.bonus)})
 total=sum(x['net'] for x in rows)
 return {'records':len(rows),'total_net':round(total,2),'average_net':round(total/len(rows),2) if rows else 0,'trend':rows[-12:]}
