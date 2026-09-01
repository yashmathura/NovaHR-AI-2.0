import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.shortcuts import render
from .service import run_agent
from agent.analytics.insights import snapshot
from core.models import AIConversation,AIMessage,AIQueryFeedback

@login_required
@ensure_csrf_cookie
def chat_page(request): return render(request,'agent.html')
@login_required
@ensure_csrf_cookie
def chat_api(request):
 if request.method!='POST': return JsonResponse({'ok':False,'message':'POST required'},status=405)
 try:data=json.loads(request.body);message=(data.get('message') or '').strip();cid=data.get('conversation_id')
 except Exception:return JsonResponse({'ok':False,'message':'Invalid JSON'},status=400)
 if not message:return JsonResponse({'ok':False,'message':'Message is required'},status=400)
 return JsonResponse(run_agent(request.user,message,cid))
@login_required
def analytics_api(request): return JsonResponse({'ok':True,'data':snapshot()})
@login_required
def conversations_api(request):
 rows=list(AIConversation.objects.filter(user=request.user).values('id','title','created_at','updated_at')[:50]);return JsonResponse({'ok':True,'conversations':rows},safe=True)
@login_required
def feedback_api(request):
 if request.method!='POST':return JsonResponse({'ok':False},status=405)
 try:d=json.loads(request.body);m=AIMessage.objects.get(id=d.get('message_id'),conversation__user=request.user);AIQueryFeedback.objects.create(message=m,rating=max(1,min(5,int(d.get('rating',3)))),feedback=d.get('feedback',''));return JsonResponse({'ok':True})
 except Exception as e:return JsonResponse({'ok':False,'message':str(e)},status=400)
