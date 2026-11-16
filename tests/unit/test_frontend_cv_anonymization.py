import unittest
from unittest.mock import Mock, patch

from backend.controller import (
	submit_anonymization,
)
from backend.manager.cv.rizzo_anonymizer import RizzoAnonymizer


class FrontendCVAnonymizationTests(unittest.TestCase):
	@patch("backend.manager.cv.rizzo_anonymizer.sleep")
	def test_waits_for_model_before_anonymizing(self, sleep):
		get_status = Mock(
			side_effect=[
				{"available": False, "state": "downloading"},
				{"available": True, "state": "loading"},
				{"available": True, "state": "ready"},
			]
		)
		anonymize = Mock(return_value="CV anonimizzato")

		result = RizzoAnonymizer._anonymize_when_ready(
			"CV originale",
			anonymize,
			get_status,
		)

		self.assertEqual(result, "CV anonimizzato")
		self.assertEqual(get_status.call_count, 3)
		anonymize.assert_called_once_with("CV originale")
		self.assertEqual(sleep.call_count, 2)

	def test_background_task_runs_anonymization_when_model_is_ready(self):
		anonymize = Mock(return_value="CV anonimizzato")
		get_status = Mock(return_value={"available": True, "state": "ready"})

		future = submit_anonymization("CV originale", anonymize, get_status)

		self.assertEqual(future.result(timeout=5), "CV anonimizzato")
		anonymize.assert_called_once_with("CV originale")

	@patch("backend.manager.cv.rizzo_anonymizer.sleep")
	def test_model_error_fails_without_calling_anonymizer(self, sleep):
		anonymize = Mock()
		get_status = Mock(return_value={"available": False, "state": "error"})

		with self.assertRaisesRegex(RuntimeError, "preparazione del modello"):
			RizzoAnonymizer._anonymize_when_ready(
				"CV originale",
				anonymize,
				get_status,
			)

		anonymize.assert_not_called()
		sleep.assert_not_called()

	def test_rejects_empty_cv_text(self):
		with self.assertRaisesRegex(ValueError, "testo del CV"):
			submit_anonymization("  ", Mock(), Mock())


if __name__ == "__main__":
	unittest.main()
