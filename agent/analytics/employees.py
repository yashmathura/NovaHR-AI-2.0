from django.db.models import Count
from core.models import User
def summary(): return {'total':User.objects.filter(is_active=True).count(),'roles':list(User.objects.values('role').annotate(count=Count('id')))}
