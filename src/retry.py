from src.state import LessonState


MAX_RETRIES = 2


def record_rejection(state: LessonState) -> dict:
    failed_checks = [
        {
            "criterion": check["criterion"],
            "reason": check["reason"],
            "evidence": check["evidence"],
            "required_fix": check["required_fix"],
        }
        for check in state["evaluation"]["checks"]
        if not check["passed"]
    ]
    rejection_entry = {
        "attempt": state["retry_count"] + 1,
        "failed_checks": failed_checks,
        "rejected_lesson": state["lesson"],
    }
    return {
        "rejection_history": [*state["rejection_history"], rejection_entry]
    }
