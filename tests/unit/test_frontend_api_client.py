import unittest
from unittest.mock import Mock, patch

import requests
from fastapi import HTTPException

from interops.api_client import HireReadyApiClient


class HireReadyApiClientTests(unittest.TestCase):
	@patch("frontend.api_client.requests.request")
	def test_uploads_document_to_backend(self, request):
		response = Mock(ok=True, status_code=200)
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
		response.status_code = 422
		response.json.return_value = {"detail": "Modello non disponibile"}
		request.return_value = response
		client = HireReadyApiClient()

		with self.assertRaises(HTTPException) as raised:
			client.anonymization_available()

		self.assertEqual(raised.exception.status_code, 422)
		self.assertEqual(
			raised.exception.detail,
			"Errore client HTTP 422: Modello non disponibile",
		)

	def test_classifies_redirect_client_and_server_http_errors(self):
		client = HireReadyApiClient()
		for status_code, category in (
			(302, "Reindirizzamento HTTP"),
			(404, "Errore client HTTP"),
			(503, "Errore server HTTP"),
		):
			with self.subTest(status_code=status_code):
				response = Mock(
					status_code=status_code,
					text="dettaglio originato dal server",
					reason="",
				)
				response.json.side_effect = ValueError("non JSON")

				with self.assertRaises(HTTPException) as raised:
					client._raise_for_http_error(response)

				self.assertEqual(raised.exception.status_code, status_code)
				self.assertEqual(
					raised.exception.detail,
					f"{category} {status_code}: dettaglio originato dal server",
				)

	@patch(
		"frontend.api_client.requests.request",
		side_effect=requests.ConnectionError("connection refused"),
	)
	def test_reports_backend_unavailable(self, request):
		client = HireReadyApiClient()

		with self.assertRaises(HTTPException) as raised:
			client.anonymize_cv("CV")

		self.assertEqual(raised.exception.status_code, 503)
		self.assertIn("connection refused", raised.exception.detail)

	@patch("frontend.api_client.requests.request")
	def test_pdf_download_preserves_backend_http_status_and_detail(self, request):
		response = Mock(ok=False, status_code=500)
		response.json.return_value = {"detail": "Errore interno del backend"}
		request.return_value = response
		client = HireReadyApiClient()

		with self.assertRaises(HTTPException) as raised:
			client.download_report_pdf({})

		self.assertEqual(raised.exception.status_code, 500)
		self.assertEqual(
			raised.exception.detail,
			"Errore server HTTP 500: Errore interno del backend",
		)

	@patch(
		"frontend.api_client.requests.request",
		side_effect=ValueError("invalid request configuration"),
	)
	def test_unexpected_request_error_exposes_original_exception(self, request):
		client = HireReadyApiClient()

		with self.assertRaises(HTTPException) as raised:
			client.anonymize_cv("CV")

		self.assertEqual(raised.exception.status_code, 500)
		self.assertEqual(
			raised.exception.detail,
			"ValueError: invalid request configuration",
		)

	@patch("frontend.api_client.requests.request")
	def test_invalid_success_response_exposes_json_error(self, request):
		response = Mock(ok=True, status_code=200)
		response.json.side_effect = ValueError("invalid JSON payload")
		request.return_value = response
		client = HireReadyApiClient()

		with self.assertRaises(HTTPException) as raised:
			client.anonymization_status()

		self.assertEqual(raised.exception.status_code, 502)
		self.assertEqual(raised.exception.detail, "ValueError: invalid JSON payload")

	def test_interview_closes_when_answer_language_is_not_italian(self):
		self.assertTrue(
			HireReadyApiClient.is_interview_closed(
				{
					"is_final": False,
					"is_meaningful": {
						"azione": "prosegui",
						"lingua": "Inglese",
					},
				}
			)
		)
		self.assertFalse(
			HireReadyApiClient.is_interview_closed(
				{
					"is_final": False,
					"is_meaningful": {
						"azione": "prosegui",
						"lingua": "Italiano",
					},
				}
			)
		)

	def test_final_message_requires_final_phase_and_flag(self):
		final_turn = {"phase": "finale", "is_final": True}
		self.assertTrue(HireReadyApiClient.is_final_turn(final_turn))
		self.assertEqual(
			HireReadyApiClient.turn_message(final_turn),
			"Grazie per aver partecipato al colloquio!",
		)
		self.assertFalse(
			HireReadyApiClient.is_final_turn(
				{"phase": "tecnica", "is_final": True}
			)
		)
		self.assertFalse(
			HireReadyApiClient.is_final_turn(
				{"phase": "finale", "is_final": False}
			)
		)
		self.assertFalse(
			HireReadyApiClient.is_final_turn(
				{
					"phase": "finale",
					"is_final": True,
					"closure_reason": "profile_contradiction",
				}
			)
		)
		self.assertIn(
			"informazioni incompatibili",
			HireReadyApiClient.turn_message(
				{
					"phase": "finale",
					"is_final": True,
					"closure_reason": "profile_contradiction",
					"is_meaningful": {"azione": "prosegui"},
				}
			),
		)
		self.assertEqual(
			HireReadyApiClient.turn_message(
				{"phase": "tecnica", "is_final": True}
			),
			"In attesa della prossima domanda…",
		)

	@patch("frontend.api_client.requests.request")
	def test_posts_anonymized_cv_and_selected_position_for_parsing(self, request):
		response = Mock(ok=True, status_code=200)
		response.json.return_value = {
			"selected_position": "ML Engineer",
			"anonymized_cv": "CV [PERSON]",
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
		self.assertEqual(result["anonymized_cv"], "CV [PERSON]")
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
		response = Mock(ok=True, status_code=200)
		response.json.return_value = {"turn": {}, "history": [], "is_closed": False}
		request.return_value = response
		client = HireReadyApiClient()

		client.interview(
			anonymized_cv="CV [PERSON]",
			selected_position="ML Engineer",
			level_position="senior",
			position_description="Esperienza con modelli ML.",
			profile={"technical_skills": ["Python"]},
		)

		self.assertEqual(
			request.call_args.kwargs["json"],
			{
				"history": [],
				"anonymized_cv": "CV [PERSON]",
				"last_turn": None,
				"selected_position": "ML Engineer",
				"level_position": "senior",
				"position_description": "Esperienza con modelli ML.",
				"profile": {"technical_skills": ["Python"]},
			},
		)

	@patch("frontend.api_client.requests.request")
	def test_posts_anonymized_cv_with_each_follow_up_turn(self, request):
		response = Mock(ok=True, status_code=200)
		response.json.return_value = {"turn": {}, "history": [], "is_closed": False}
		request.return_value = response
		client = HireReadyApiClient()

		client.interview(
			anonymized_cv="CV [PERSON]",
			history=[{"role": "user", "content": "Risposta precedente"}],
			last_turn={"turn_id": 1},
			candidate_answer="Risposta attuale",
		)

		self.assertEqual(
			request.call_args.kwargs["json"],
			{
				"history": [{"role": "user", "content": "Risposta precedente"}],
				"anonymized_cv": "CV [PERSON]",
				"last_turn": {"turn_id": 1},
				"candidate_answer": "Risposta attuale",
			},
		)

	@patch("frontend.api_client.requests.request")
	def test_posts_interview_report_data(self, request):
		response = Mock(ok=True, status_code=200)
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

	@patch("frontend.api_client.requests.request")
	def test_downloads_interview_report_pdf(self, request):
		response = Mock(
			ok=True,
			status_code=200,
			content=b"%PDF-report",
			headers={
				"Content-Disposition": (
					'attachment; filename="report_colloquio_3.pdf"'
				)
			},
		)
		request.return_value = response
		client = HireReadyApiClient("http://127.0.0.1:8010")
		report = {
			"summary": "Report.",
			"intervention_points": [],
			"contenuto": "",
			"answers": [],
			"score": None,
		}

		pdf, filename = client.download_report_pdf(report)

		self.assertEqual(pdf, b"%PDF-report")
		self.assertEqual(filename, "report_colloquio_3.pdf")
		args, kwargs = request.call_args
		self.assertEqual(
			args[:2],
			("POST", "http://127.0.0.1:8010/api/report/pdf"),
		)
		self.assertEqual(kwargs["json"], report)

	@patch("frontend.api_client.requests.request")
	def test_rejects_report_pdf_response_without_download_filename(self, request):
		request.return_value = Mock(
			ok=True,
			status_code=200,
			content=b"%PDF-report",
			headers={},
		)

		with self.assertRaisesRegex(HTTPException, "non contiene il nome del PDF"):
			HireReadyApiClient("http://127.0.0.1:8010").download_report_pdf({})


if __name__ == "__main__":
	 unittest.main()