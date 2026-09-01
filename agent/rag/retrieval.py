from core.models import DocumentChunk
from .embeddings import embed,cosine
def retrieve(query,top_k=4):
 q=embed(query); scored=[]
 for c in DocumentChunk.objects.select_related('document').all(): scored.append((cosine(q,c.embedding or []),c))
 scored.sort(key=lambda x:x[0],reverse=True)
 return [{'score':round(s,3),'title':c.document.title,'content':c.content,'document_id':c.document_id} for s,c in scored[:top_k] if s>0]
