import os
def configured(): return bool(os.getenv('LLM_API_KEY')) and os.getenv('LLM_PROVIDER','none')!='none'
def status(): return {'provider':os.getenv('LLM_PROVIDER','local-safe'),'configured':configured(),'mode':'optional'}
