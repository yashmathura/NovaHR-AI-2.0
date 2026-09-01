from django.core.management.base import BaseCommand
from agent.novalm import train

class Command(BaseCommand):
    help="Train the NovaLM Transformer language-understanding model from scratch."
    def add_arguments(self,parser): parser.add_argument("--epochs",type=int,default=18)
    def handle(self,*args,**opts):
        result=train(opts["epochs"]); self.stdout.write(self.style.SUCCESS("NovaLM trained successfully."));
        for k,v in result.items(): self.stdout.write(f"{k}: {v}")
