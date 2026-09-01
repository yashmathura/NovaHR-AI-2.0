def normalize_rating(value):
 try:return max(1,min(5,int(value)))
 except Exception:return 3
