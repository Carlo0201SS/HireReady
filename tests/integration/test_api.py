import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import app


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

	@patch("backend.api.is_anonymization_available", return_value=True)
	def test_anonymization_status(self, is_available):
		response = self.client.get("/api/anonymization/status")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {"available": True})
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

	@patch("backend.api.anonymize_cv", return_value="[PERSON], [EMAIL]")
	def test_anonymize_endpoint(self, anonymize):
		response = self.client.post(
			"/api/cv/anonymize",
			json={"text": "Ada Lovelace, ada@example.com"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {"text": "[PERSON], [EMAIL]"})
		anonymize.assert_called_once_with("Ada Lovelace, ada@example.com")


if __name__ == "__main__":
	 unittest.main()