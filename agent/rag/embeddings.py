import re,hashlib
def embed(text,dims=64):
 v=[0.0]*dims
 for w in re.findall(r'[a-z0-9]+',(text or '').lower()):
  i=int(hashlib.sha256(w.encode()).hexdigest(),16)%dims;v[i]+=1.0
 n=sum(x*x for x in v)**0.5 or 1.0;return [x/n for x in v]
def cosine(a,b): return sum(x*y for x,y in zip(a,b))
