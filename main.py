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
print("=== GENERATED LESSON ===")
print(result["lesson"])
print("\n=== RUN SUMMARY ===")
print(f"Sources used: {len(result['sources'])}")
print(f"Lesson characters: {len(result['lesson'])}")
