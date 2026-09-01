from django.urls import path
from .views import chat_page,chat_api,analytics_api,conversations_api,feedback_api
urlpatterns=[path('',chat_page,name='agent_chat'),path('api/',chat_api,name='agent_api'),path('api/analytics/',analytics_api,name='agent_analytics'),path('api/conversations/',conversations_api,name='agent_conversations'),path('api/feedback/',feedback_api,name='agent_feedback')]
