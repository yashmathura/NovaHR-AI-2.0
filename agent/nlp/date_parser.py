from datetime import date,timedelta
def parse_relative(text):
    t=(text or '').lower(); today=date.today()
    if 'today' in t or 'aaj' in t:return {'start':today,'end':today,'label':'today'}
    if 'yesterday' in t or 'kal' in t:
        d=today-timedelta(days=1);return {'start':d,'end':d,'label':'yesterday'}
    if 'this month' in t:return {'start':today.replace(day=1),'end':today,'label':'this month'}
    if 'last month' in t:
        e=today.replace(day=1)-timedelta(days=1);return {'start':e.replace(day=1),'end':e,'label':'last month'}
    return {}
