def chunk_text(text,size=700,overlap=120):
 text=(text or '').strip(); out=[]; i=0
 while i<len(text): out.append(text[i:i+size]); i+=max(1,size-overlap)
 return out or ['']
