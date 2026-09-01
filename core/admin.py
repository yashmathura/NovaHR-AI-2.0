from django.contrib import admin
from .models import *
for model in [Company,Department,Team,User,Attendance,Leave,Payroll,Task,KnowledgeDocument,Notification,AgentAuditLog,AIConversation,AIMessage,DocumentChunk,AIInsight,AIQueryFeedback]:
    try: admin.site.register(model)
    except admin.sites.AlreadyRegistered: pass
