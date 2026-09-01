POS={'good','great','happy','excellent','thanks','thank'};NEG={'bad','stress','stressed','angry','poor','unfair','problem','issue','worried'}
def analyze_sentiment(text):
 t=set((text or '').lower().split()); p=len(t&POS); n=len(t&NEG); return {'label':'positive' if p>n else 'negative' if n>p else 'neutral','score':p-n}
