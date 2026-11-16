import json
import unittest
from unittest.mock import Mock

from backend.manager.llm.gemma_report import GemmaInterviewReporter


class GemmaInterviewReporterTests(unittest.TestCase):
	def test_summarizes_conversation_with_json_schema_and_motivation(self):
		lm_studio = Mock()
		lm_studio.chat_completions.return_value = (
			200,
			json.dumps(
				{
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"summary": "Esperienza in sviluppo Python.",
										"intervention_points": [
											{
												"area": "Testing delle API",
												"evidence": "Ha descritto lo sviluppo di API senza citare test.",
												"recommendation": "Approfondire test unitari e di integrazione sulle API.",
											}
										],
									}
								)
							}
						}
					]
				}
			),
		)
		reporter = GemmaInterviewReporter(lm_studio=lm_studio)
		history = [
			{"role": "system", "content": "Prompt interno"},
			{"role": "user", "content": "Ho sviluppato API in Python."},
			{"role": "assistant", "content": "Raccontami un progetto."},
		]

		summary = reporter.summarize(
			history,
			"Il colloquio è terminato regolarmente.",
		)

		self.assertEqual(summary.summary, "Esperienza in sviluppo Python.")
		self.assertEqual(summary.intervention_points[0].area, "Testing delle API")
		model, messages, response_format = lm_studio.chat_completions.call_args.args
		self.assertEqual(lm_studio.chat_completions.call_args.kwargs["temperature"], 0.2)
		self.assertEqual(model, "google/gemma-4-e2b")
		self.assertNotIn("Prompt interno", messages[1]["content"])
		self.assertIn("Il colloquio è terminato regolarmente.", messages[1]["content"])
		report_input = json.loads(messages[1]["content"])
		self.assertEqual(report_input["conversation_history"][0]["role"], "user")
		self.assertEqual(
			report_input["final_is_meaningful_motivation"],
			"Il colloquio è terminato regolarmente.",
		)
		self.assertEqual(
			response_format["json_schema"]["schema"]["properties"][
				"intervention_points"
			]["type"],
			"array",
		)

	def test_rejects_nonconforming_summary(self):
		lm_studio = Mock()
		lm_studio.chat_completions.return_value = (
			200,
			json.dumps({"choices": [{"message": {"content": '{"summary":"Test"}'}}]}),
		)
		reporter = GemmaInterviewReporter(lm_studio=lm_studio)

		with self.assertRaisesRegex(RuntimeError, "non conforme allo schema"):
			reporter.summarize([], "")


if __name__ == "__main__":
	unittest.main()
