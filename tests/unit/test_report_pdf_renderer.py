import unittest

import pymupdf

from backend.manager.report.reportlab_pdf_renderer import ReportLabPdfRenderer


class ReportLabPdfRendererTests(unittest.TestCase):
	def test_renders_all_report_content_and_escapes_markup(self):
		pdf = ReportLabPdfRenderer().render(
			{
				"summary": "<script>non eseguire</script> Sintesi del colloquio.",
				"intervention_points": [
					{
						"area": "Comunicazione",
						"evidence": "Risposte concise.",
						"recommendation": "Aggiungere esempi.",
					}
				],
				"answers": [
					{
						"question": "Descrivi un progetto.",
						"answer": "Ho realizzato un'API.",
						"motivation": "Risposta pertinente.",
						"score": 8,
					},
					{
						"question": "Seconda domanda.",
						"answer": "Risposta seconda.",
						"motivation": "Da approfondire.",
						"score": None,
					},
				],
				"score": 8.0,
			}
		)

		self.assertTrue(pdf.startswith(b"%PDF-"))
		with pymupdf.open(stream=pdf, filetype="pdf") as document:
			text = "\n".join(page.get_text() for page in document)

		self.assertIn("Media complessiva: 8.00/10", text)
		self.assertIn("Sintesi del colloquio.", text)
		self.assertIn("<script>non eseguire</script>", text)
		self.assertIn("Punti di intervento", text)
		self.assertIn("Risposta solida", text)
		self.assertIn("Voto non disponibile", text)
		self.assertIn("Motivazione / criticità", text)


if __name__ == "__main__":
	unittest.main()
