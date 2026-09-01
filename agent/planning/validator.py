from agent.permissions import check_permission
def validate(user,intent): return check_permission(getattr(user,'role','EMPLOYEE').upper(),intent) or intent.startswith('analytics_')
