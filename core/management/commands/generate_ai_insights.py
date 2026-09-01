from django.core.management.base import BaseCommand
from core.models import AIInsight
from agent.analytics.insights import snapshot,narrative
class Command(BaseCommand):
 help='Generate a deterministic HR intelligence snapshot'
 def handle(self,*args,**opts):
  d=snapshot();AIInsight.objects.create(category='WORKFORCE',title='NovaHR intelligence snapshot',content=narrative(d),data=d);self.stdout.write(self.style.SUCCESS('AI insight created.'))
