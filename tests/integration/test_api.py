import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import app
from backend.domain.models.report_model import InterviewSummary
from backend.manager.report.reportlab_pdf_renderer import ReportPdfRendererUnavailable


class HireReadyApiTests(unittest.TestCase):
	def setUp(self):
		self.client = TestClient(app)

	def test_root_returns_api_index_without_frontend_redirect(self):
		response = self.client.get("/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["service"], "HireReady API")
		self.assertEqual(response.json()["documentation"], "/docs")
		self.assertIn("cv_extraction", response.json()["endpoints"])
		self.assertNotIn("location", response.headers)

	def test_health_endpoint(self):
		response = self.client.get("/api/health")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {"status": "ok"})

	@patch("backend.api.anonymization_state", return_value="ready")
	@patch("backend.api.is_anonymization_available", return_value=True)
	def test_anonymization_status(self, is_available, state):
		response = self.client.get("/api/anonymization/status")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {"available": True, "state": "ready"})
		is_available.assert_called_once_with()

	@patch("backend.api.extract_cv_text", return_value="CV estratto")
	def test_extract_endpoint_accepts_pdf_upload(self, extract_text):
		response = self.client.post(
			"/api/cv/extract",
			files={"file": ("candidate.pdf", b"pdf bytes", "application/pdf")},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {"text": "CV estratto"})
		extract_text.assert_called_once_with("candidate.pdf", b"pdf bytes")

	@patch("backend.api.extract_cv_text", side_effect=ValueError("Il CV deve essere in formato PDF o DOCX."))
	def test_extract_endpoint_rejects_unsupported_file(self, extract_text):
		response = self.client.post(
			"/api/cv/extract",
			files={"file": ("candidate.txt", b"text", "text/plain")},
		)

		self.assertEqual(response.status_code, 415)
		self.assertIn("PDF o DOCX", response.json()["detail"])

	@patch("backend.api.extract_cv_text", side_effect=RuntimeError("Invalid PDF data"))
	def test_extract_endpoint_logs_unexpected_extraction_errors(self, extract_text):
		with self.assertLogs("backend.api", level="ERROR") as captured:
			response = self.client.post(
				"/api/cv/extract",
				files={"file": ("candidate.pdf", b"pdf bytes", "application/pdf")},
			)

		self.assertEqual(response.status_code, 422)
		self.assertEqual(
			response.json()["detail"],
			"Impossibile estrarre il testo dal documento caricato.",
		)
		self.assertIn("Invalid PDF data", "\n".join(captured.output))

	@patch("backend.api.anonymize_cv", return_value="[PERSON], [EMAIL]")
	def test_anonymize_endpoint(self, anonymize):
		response = self.client.post(
			"/api/cv/anonymize",
			json={"text": "Ada Lovelace, ada@example.com"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {"text": "[PERSON], [EMAIL]"})
		anonymize.assert_called_once_with("Ada Lovelace, ada@example.com")

	@patch("backend.api.parse_cv_for_interview")
	def test_parse_cv_for_interview_endpoint(self, parse_cv):
		parse_cv.return_value = {
			"selected_position": "Sviluppatore web React",
			"position_description": "Esperienza con API REST.",
			"anonymized_cv": "CV anonimo",
			"profile": {
				"professional_summary": "Sviluppatrice web.",
				"technical_skills": ["React", "TypeScript"],
				"relevant_experience": ["Sviluppo UI web."],
				"education": [],
				"certifications": [],
				"interview_focus": ["React"],
			},
		}
		response = self.client.post(
			"/api/cv/gemma_parse",
			json={
				"anonymized_cv": "CV anonimo",
				"selected_position": "Sviluppatore web React",
				"position_description": "Esperienza con API REST.",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["selected_position"], "Sviluppatore web React")
		self.assertEqual(response.json()["position_description"], "Esperienza con API REST.")
		self.assertEqual(response.json()["anonymized_cv"], "CV anonimo")
		self.assertEqual(response.json()["profile"]["technical_skills"], ["React", "TypeScript"])
		parse_cv.assert_called_once_with(
			anonymized_cv="CV anonimo",
			selected_position="Sviluppatore web React",
			position_description="Esperienza con API REST.",
		)

	@patch("backend.api.parse_cv_for_interview", side_effect=ValueError(
		"La descrizione inserita non sembra coerente con la posizione selezionata."
	))
	def test_parse_cv_for_interview_rejects_incoherent_position_description(self, parse_cv):
		response = self.client.post(
			"/api/cv/gemma_parse",
			json={
				"anonymized_cv": "CV anonimo",
				"selected_position": "Sviluppatore web React",
				"position_description": "Cerchiamo un cuoco per il ristorante.",
			},
		)

		self.assertEqual(response.status_code, 422)
		self.assertIn("non sembra coerente", response.json()["detail"])
		parse_cv.assert_called_once()

	@patch("backend.api.generate_interview_report")
	def test_interview_report_endpoint(self, generate_report):
		generate_report.return_value = {
			"summary": "Il candidato ha esperienza con Python.",
			"intervention_points": [],
			"contenuto": "Il colloquio è terminato regolarmente.",
			"score": 10,
			"answers": [
				{
					"question": "Raccontami un progetto.",
					"answer": "Ho realizzato un'API.",
					"motivation": "Risposta pertinente.",
					"score": 8,
				}
			],
		}

		response = self.client.post(
			"/api/report",
			json={
				"history": [{"role": "user", "content": "Ho lavorato con Python."}],
				"contenuto": "Il colloquio è terminato regolarmente.",
				"score": 10,
				"answers": [
					{
						"question": "Raccontami un progetto.",
						"answer": "Ho realizzato un'API.",
						"motivation": "Risposta pertinente.",
						"score": 8,
					}
				],
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["summary"], generate_report.return_value["summary"])
		self.assertEqual(response.json()["intervention_points"], [])
		generate_report.assert_called_once()

	@patch("backend.controller._interview_reporter")
	def test_interview_report_omits_null_scores_from_arithmetic_mean(self, get_reporter):
		get_reporter.return_value.summarize.return_value = InterviewSummary(
			summary="Riepilogo del colloquio.",
			intervention_points=[],
		)
		response = self.client.post(
			"/api/report",
			json={
				"contenuto": "Colloquio completato.",
				"score": None,
				"answers": [
					{
						"question": f"Domanda {index}",
						"answer": f"Risposta {index}",
						"motivation": "Valutata.",
						"score": index,
					}
					for index in range(1, 11)
				] + [
					{
						"question": "Domanda senza voto",
						"answer": "Risposta senza voto",
						"motivation": "Non valutabile.",
						"score": None,
					}
				],
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["score"], 5.5)
		self.assertIsNone(response.json()["answers"][-1]["score"])

	def test_interview_report_endpoint_rejects_scores_outside_range(self):
		response = self.client.post(
			"/api/report",
			json={
				"answers": [
					{
						"question": "Raccontami un progetto.",
						"answer": "Ho realizzato un'API.",
						"motivation": "Risposta pertinente.",
						"score": 11,
					}
				]
			},
		)

		self.assertEqual(response.status_code, 422)

	@patch("backend.api.generate_report_pdf", return_value=b"%PDF-report")
	def test_interview_report_pdf_endpoint_returns_downloadable_pdf(self, generate_pdf):
		report = {
			"summary": "Il candidato ha esperienza con Python.",
			"intervention_points": [],
			"contenuto": "Il colloquio è terminato regolarmente.",
			"answers": [],
			"score": 8.5,
		}

		response = self.client.post("/api/report/pdf", json=report)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.content, b"%PDF-report")
		self.assertEqual(response.headers["content-type"], "application/pdf")
		self.assertIn("attachment; filename=", response.headers["content-disposition"])
		generate_pdf.assert_called_once()

	@patch(
		"backend.api.generate_report_pdf",
		side_effect=ReportPdfRendererUnavailable(
			"ReportLab non è installato nell'ambiente Python del backend."
		),
	)
	def test_interview_report_pdf_explains_missing_native_dependency(self, generate_pdf):
		response = self.client.post(
			"/api/report/pdf",
			json={
				"summary": "Report.",
				"intervention_points": [],
				"contenuto": "",
				"answers": [],
				"score": None,
			},
		)

		self.assertEqual(response.status_code, 503)
		self.assertIn("ReportLab non è installato", response.json()["detail"])


if __name__ == "__main__":
	 unittest.main()