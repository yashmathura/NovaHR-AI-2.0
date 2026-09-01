from core.models import KnowledgeDocument,DocumentChunk
from .chunking import chunk_text
from .embeddings import embed
def ingest_document(document):
 DocumentChunk.objects.filter(document=document).delete()
 rows=[]
 for i,c in enumerate(chunk_text(document.content)):
  rows.append(DocumentChunk(document=document,content=c,chunk_index=i,embedding=embed(c)))
 return DocumentChunk.objects.bulk_create(rows)
def ingest_all():
 return sum(len(ingest_document(d)) for d in KnowledgeDocument.objects.all())
