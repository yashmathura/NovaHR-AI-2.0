from .retrieval import retrieve

def answer_context(query): return retrieve(query)
def answer(query):
 rows=retrieve(query)
 if not rows: return {'answer':'I could not find a matching policy document.','sources':[]}
 parts=[]; sources=[]
 for row in rows[:3]:
  content=row.get('content','') if isinstance(row,dict) else str(row)
  title=row.get('title','Policy') if isinstance(row,dict) else 'Policy'
  if content: parts.append(content[:500]); sources.append(title)
 return {'answer':'\n\n'.join(parts) or 'I found relevant policy information.','sources':sources,'matches':rows}
