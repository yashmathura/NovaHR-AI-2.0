from core.models import AIConversation,AIMessage
def get_or_create(user,conversation_id=None):
 if conversation_id:
  c=AIConversation.objects.filter(id=conversation_id,user=user).first()
  if c:return c
 return AIConversation.objects.create(user=user,title='NovaHR conversation')
def recent_context(conv,limit=8): return list(conv.messages.order_by('-created_at')[:limit].values('role','content','metadata'))[::-1]
def save_message(conv,role,content,metadata=None): return AIMessage.objects.create(conversation=conv,role=role,content=content,metadata=metadata or {})
