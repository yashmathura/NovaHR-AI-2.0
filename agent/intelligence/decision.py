def needs_rag(intent): return intent=='get_policy'
def needs_analytics(message): return any(x in (message or '').lower() for x in ['analyze','analytics','summary','insight'])
