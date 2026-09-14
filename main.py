from src.graph import graph


initial_state = {
    "topic": "Introduction to RAG",
    "grounding_context": "",
    "sources": [],
    "memory_guidance": [],
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
print(f"Lesson words: {len(result['lesson'].split())}")
print(f"Lesson characters: {len(result['lesson'])}")
print(f"Retries used: {result['retry_count']}")
print(f"Rejected attempts: {len(result['rejection_history'])}")
print(f"Memory guidance loaded: {len(result['memory_guidance'])}")
for guidance in result["memory_guidance"]:
    print(f"- {guidance}")
print("\n=== EVALUATION ===")
for check in result["evaluation"]["checks"]:
    status = "PASS" if check["passed"] else "FAIL"
    print(f"{check['criterion']}: {status}")
    print(f"Reason: {check['reason']}")
    if check["required_fix"]:
        print(f"Required fix: {check['required_fix']}")
    print()

overall_status = "PASS" if result["evaluation"]["overall_pass"] else "FAIL"
print(f"OVERALL: {overall_status}")

if result["rejection_history"]:
    print("\n=== REJECTION SUMMARY ===")
    for rejection in result["rejection_history"]:
        print(f"Attempt {rejection['attempt']} rejected:")
        for check in rejection["failed_checks"]:
            print(f"- {check['criterion']}")
