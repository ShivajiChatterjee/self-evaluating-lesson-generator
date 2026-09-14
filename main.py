import argparse

from src.workflow import run_lesson_workflow


parser = argparse.ArgumentParser(
    description="Generate and evaluate a grounded beginner lesson."
)
parser.add_argument("--topic", default="Introduction to RAG")
args = parser.parse_args()

result = run_lesson_workflow(args.topic)
print("=== GENERATED LESSON ===")
print(result["lesson"])
print("\n=== RUN SUMMARY ===")
print(f"Sources used: {len(result['sources'])}")
for source in result["sources"]:
    print(f"- {source}")
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
