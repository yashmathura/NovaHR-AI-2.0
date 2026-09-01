from django.db.models import Count
from core.models import Task
def summary(): return {x['status']:x['count'] for x in Task.objects.values('status').annotate(count=Count('id'))}
