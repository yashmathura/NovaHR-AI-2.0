from agent.router import resolve_intent
from .normalizer import normalize_query
def classify_intent(text):
 q=normalize_query(text); intent=resolve_intent(q); return {'intent':intent,'confidence':0.85 if intent!='UNKNOWN' else 0.0,'normalized':q}
