import unittest
from unittest.mock import Mock, patch

import requests

from interops.api_client import BackendApiError, HireReadyApiClient


class HireReadyApiClientTests(unittest.TestCase):
	@patch("frontend.api_client.requests.request")
	def test_uploads_document_to_backend(self, request):
		response = Mock(ok=True)
		response.json.return_value = {"text": "CV estratto"}
		request.return_value = response
		client = HireReadyApiClient("http://127.0.0.1:8010")

		text = client.extract_cv_text("cv.pdf", b"pdf-bytes")

		self.assertEqual(text, "CV estratto")
		args, kwargs = request.call_args
		self.assertEqual(args[:2], ("POST", "http://127.0.0.1:8010/api/cv/extract"))
		self.assertEqual(kwargs["files"], {"file": ("cv.pdf", b"pdf-bytes")})

	@patch("frontend.api_client.requests.request")
	def test_returns_backend_error_detail(self, request):
		response = Mock(ok=False)
		response.json.return_value = {"detail": "Modello non disponibile"}
		request.return_value = response
		client = HireReadyApiClient()

		with self.assertRaisesRegex(BackendApiError, "Modello non disponibile"):
			client.anonymization_available()

	@patch("frontend.api_client.requests.request", side_effect=requests.ConnectionError)
	def test_reports_backend_unavailable(self, request):
		client = HireReadyApiClient()

		with self.assertRaisesRegex(BackendApiError, "FastAPI sia avviato"):
			client.anonymize_cv("CV")

	@patch("frontend.api_client.requests.request")
	def test_posts_anonymized_cv_and_selected_position_for_parsing(self, request):
		response = Mock(ok=True)
		response.json.return_value = {
			"selected_position": "ML Engineer",
			"profile": {"technical_skills": ["Python"]},
		}
		request.return_value = response
		client = HireReadyApiClient()

		result = client.parse_cv_for_interview(
			"CV [EMAIL]",
			"ML Engineer",
			position_description="Esperienza con modelli ML.",
		)

		self.assertEqual(result["selected_position"], "ML Engineer")
		args, kwargs = request.call_args
		self.assertEqual(args[:2], ("POST", "http://127.0.0.1:8000/api/cv/gemma_parse"))
		self.assertEqual(
			kwargs["json"],
			{
				"anonymized_cv": "CV [EMAIL]",
				"selected_position": "ML Engineer",
				"position_description": "Esperienza con modelli ML.",
			},
		)

	@patch("frontend.api_client.requests.request")
	def test_posts_position_description_when_starting_interview(self, request):
		response = Mock(ok=True)
		response.json.return_value = {"turn": {}, "history": [], "is_closed": False}
		request.return_value = response
		client = HireReadyApiClient()

		client.interview(
			selected_position="ML Engineer",
			position_description="Esperienza con modelli ML.",
			profile={"technical_skills": ["Python"]},
		)

		self.assertEqual(
			request.call_args.kwargs["json"],
			{
				"history": [],
				"last_turn": None,
				"selected_position": "ML Engineer",
				"position_description": "Esperienza con modelli ML.",
				"profile": {"technical_skills": ["Python"]},
			},
		)

	@patch("frontend.api_client.requests.request")
	def test_posts_interview_report_data(self, request):
		response = Mock(ok=True)
		response.json.return_value = {"summary": "Esperienza in Python.", "answers": []}
		request.return_value = response
		client = HireReadyApiClient()
		history = [{"role": "user", "content": "Ho lavorato con Python."}]
		answers = [
			{
				"question": "Raccontami un progetto.",
				"answer": "Ho realizzato un'API.",
				"motivation": "Risposta pertinente.",
				"score": 8,
			}
		]

		result = client.generate_report(
			history=history,
			contenuto="Colloquio completato.",
			answers=answers,
			score=None,
		)

		self.assertEqual(result["summary"], "Esperienza in Python.")
		args, kwargs = request.call_args
		self.assertEqual(args[:2], ("POST", "http://127.0.0.1:8000/api/report"))
		self.assertEqual(
			kwargs["json"],
			{
				"history": history,
				"contenuto": "Colloquio completato.",
				"answers": answers,
				"score": None,
			},
		)


if __name__ == "__main__":
	 unittest.main()