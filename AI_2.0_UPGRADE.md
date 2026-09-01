# NovaHR AI 2.0

Implemented phases 1-8:
1. NLP normalization, entities, dates and sentiment
2. Persistent conversation memory
3. RAG knowledge chunks and semantic retrieval
4. HR analytics
5. Optional LLM abstraction with deterministic fallback
6. Intelligence orchestration
7. Insights and feedback
8. Multi-step planning primitives

## Install
`pip install -r requirements.txt`
`python manage.py migrate`
`python manage.py ingest_knowledge`
`python manage.py generate_ai_insights`
`python manage.py runserver`

Existing deterministic agent, RBAC and ORM tools remain authoritative. No external LLM is required for the project to run.
