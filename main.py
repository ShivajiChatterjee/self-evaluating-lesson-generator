from src.graph import graph


initial_state = {
    "topic": "Introduction to RAG",
    "grounding_context": "",
    "sources": [],
    "lesson": "",
    "evaluation": {},
    "retry_count": 0,
    "rejection_history": [],
}

result = graph.invoke(initial_state)
print("=== GROUNDING LOADED ===")
print(f"Sources: {len(result['sources'])}")
print(f"Characters loaded: {len(result['grounding_context'])}")
