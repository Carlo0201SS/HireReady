from collections.abc import MutableMapping
from typing import Any


_INTERVIEW_SESSION_KEYS = (
	"interview_turn",
	"interview_history",
	"interview_closed",
	"interview_report_answers",
	"interview_report",
	"answer_counter",
)


def reset_interview_session(session_state: MutableMapping[str, Any]) -> None:
	for key in _INTERVIEW_SESSION_KEYS:
		session_state.pop(key, None)
