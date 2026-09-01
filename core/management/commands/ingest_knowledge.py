from django.core.management.base import BaseCommand
from agent.rag.ingestion import ingest_all
class Command(BaseCommand):
 help='Build semantic chunks for KnowledgeDocument records'
 def handle(self,*args,**opts): self.stdout.write(self.style.SUCCESS(f'Created {ingest_all()} document chunks.'))
