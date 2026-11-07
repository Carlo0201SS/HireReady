import unittest

from backend.controller import reset_interview_session


class InterviewSessionTests(unittest.TestCase):
	def test_reset_clears_previous_interview_but_preserves_cv_context(self):
		session_state = {
			"interview_turn": {"turn_id": 1},
			"interview_history": [{"role": "assistant", "content": "Seconda domanda"}],
			"interview_closed": False,
			"interview_report_answers": [{"score": 8}],
			"interview_report": {"summary": "Report precedente"},
			"answer_counter": 1,
			"cv_interview_context": {"selected_position": "Sviluppatore React"},
			"extracted_cv_text": "CV caricato",
		}

		reset_interview_session(session_state)

		self.assertNotIn("interview_turn", session_state)
		self.assertNotIn("interview_history", session_state)
		self.assertNotIn("interview_closed", session_state)
		self.assertNotIn("interview_report_answers", session_state)
		self.assertNotIn("interview_report", session_state)
		self.assertNotIn("answer_counter", session_state)
		self.assertIn("cv_interview_context", session_state)
		self.assertIn("extracted_cv_text", session_state)


if __name__ == "__main__":
	unittest.main()
