import unittest
from unittest.mock import Mock, patch
import json

from pydantic import ValidationError
import requests

from backend.application.cv_parser_orchestrator import CVParserOrchestrator
from backend.domain.models.api_model import CVParserRequest
from backend.domain.models.cv_model import CVInterviewContext, CVParsedProfile
from backend.manager.llm.gemma_cv_parser import GemmaCVParser
from interops.lm_studio_client import LMStudioAPI, LMStudioUnavailableError


PROFILE = {
	"professional_summary": "Sviluppatrice con esperienza in applicazioni web.",
	"technical_skills": ["React", "TypeScript"],
	"relevant_experience": ["Sviluppo di interfacce web accessibili."],
	"education": [],
	"certifications": [],
	"interview_focus": ["Architettura React", "Accessibilita' web"],
}


class CVParserContractTests(unittest.TestCase):
	def test_request_requires_anonymized_cv_and_selected_position(self):
		request = CVParserRequest(
			anonymized_cv="CV anonimizzato",
			selected_position="Sviluppatore web React",
		)

		self.assertEqual(request.selected_position, "Sviluppatore web React")
		with self.assertRaises(ValidationError):
			CVParserRequest(anonymized_cv=" ", selected_position="React")

	def test_context_is_validated_and_generates_schema(self):
		context = CVInterviewContext.model_validate(
			{
				"selected_position": "Sviluppatore web React",
				"profile": PROFILE,
			}
		)
		schema = type(context).model_json_schema()

		self.assertEqual(context.profile.technical_skills, ["React", "TypeScript"])
		self.assertIn("interview_focus", schema["$defs"]["CVParsedProfile"]["properties"])


class CVParserOrchestratorTests(unittest.TestCase):
	def test_returns_context_with_selected_position_and_parsed_profile(self):
		parser = Mock()
		parser.parse.return_value = CVParsedProfile.model_validate(PROFILE)
		orchestrator = CVParserOrchestrator(parser)

		context = orchestrator.parse_for_interview(
			anonymized_cv="CV con dati anonimizzati",
			selected_position="Sviluppatore web React",
		)

		self.assertEqual(context.selected_position, "Sviluppatore web React")
		self.assertEqual(context.profile.technical_skills, ["React", "TypeScript"])
		parser.parse.assert_called_once_with("CV con dati anonimizzati", "Sviluppatore web React")

	def test_rejects_missing_inputs_without_calling_parser(self):
		parser = Mock()
		orchestrator = CVParserOrchestrator(parser)

		with self.assertRaises(ValueError):
			orchestrator.parse_for_interview(anonymized_cv=" ", selected_position="React")
		with self.assertRaises(ValueError):
			orchestrator.parse_for_interview(anonymized_cv="CV anonimo", selected_position=" ")

		parser.parse.assert_not_called()


class GemmaCVParserTests(unittest.TestCase):
	def test_sends_anonymized_cv_and_position_with_json_schema_via_interops(self):
		lm_studio = Mock()
		lm_studio.chat_completions.return_value = (
			200,
			json.dumps({"choices": [{"message": {"content": json.dumps(PROFILE)}}]}),
		)
		parser = GemmaCVParser(lm_studio=lm_studio, model="google/gemma-4-e2b")

		profile = parser.parse("CV [EMAIL]", "Sviluppatore web React")

		self.assertEqual(profile.technical_skills, ["React", "TypeScript"])
		model, messages, response_format = lm_studio.chat_completions.call_args.args
		self.assertEqual(
			lm_studio.chat_completions.call_args.kwargs["temperature"],
			0.2,
		)
		self.assertEqual(model, "google/gemma-4-e2b")
		self.assertIn("CV [EMAIL]", messages[1]["content"])
		self.assertIn("Sviluppatore web React", messages[1]["content"])
		self.assertEqual(
			response_format["json_schema"]["schema"],
			CVParsedProfile.model_json_schema(),
		)

	def test_rejects_nonconforming_model_output(self):
		lm_studio = Mock()
		lm_studio.chat_completions.return_value = (
			200,
			json.dumps({"choices": [{"message": {"content": "{}"}}]}),
		)
		parser = GemmaCVParser(lm_studio=lm_studio)

		with self.assertRaisesRegex(RuntimeError, "non conforme allo schema"):
			parser.parse("CV anonimizzato", "ML Engineer")

	def test_reports_lm_studio_unavailable(self):
		lm_studio = Mock()
		lm_studio.chat_completions.side_effect = LMStudioUnavailableError("LM Studio giù")
		parser = GemmaCVParser(lm_studio=lm_studio)

		with self.assertRaisesRegex(RuntimeError, "LM Studio giù"):
			parser.parse("CV anonimizzato", "ML Engineer")


class LMStudioAPITests(unittest.TestCase):
	@patch("interops.lm_studio_client.requests.request")
	def test_chat_completions_posts_to_openai_compatible_endpoint(self, request):
		request.return_value = Mock(status_code=200, text="{}")
		api = LMStudioAPI("http://127.0.0.1:1234/", "test-key", timeout=5)

		status, _ = api.chat_completions("m", [{"role": "user", "content": "ciao"}], {"type": "json_schema"})

		self.assertEqual(status, 200)
		args, kwargs = request.call_args
		self.assertEqual(args, ("POST", "http://127.0.0.1:1234/v1/chat/completions"))
		self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
		self.assertEqual(kwargs["json"]["response_format"], {"type": "json_schema"})
		self.assertEqual(kwargs["json"]["temperature"], 0.2)
		self.assertEqual(kwargs["timeout"], 5)

	@patch("interops.lm_studio_client.requests.request")
	def test_chat_completions_accepts_adjustable_temperature(self, request):
		request.return_value = Mock(status_code=200, text="{}")
		api = LMStudioAPI("http://127.0.0.1:1234", "test-key")

		api.chat_completions(
			"m",
			[{"role": "user", "content": "ciao"}],
			temperature=0.7,
		)

		self.assertEqual(request.call_args.kwargs["json"]["temperature"], 0.7)

	def test_chat_completions_rejects_temperature_outside_range(self):
		api = LMStudioAPI("http://127.0.0.1:1234", "test-key")

		for temperature in (-0.1, 1.1):
			with self.subTest(temperature=temperature):
				with self.assertRaisesRegex(ValueError, "tra 0 e 1"):
					api.chat_completions(
						"m",
						[{"role": "user", "content": "ciao"}],
						temperature=temperature,
					)

	@patch("interops.lm_studio_client.requests.request", side_effect=requests.ConnectionError)
	def test_wraps_network_errors(self, request):
		with self.assertRaises(LMStudioUnavailableError):
			LMStudioAPI("http://127.0.0.1:1234", "").get_list_models()


if __name__ == "__main__":
	 unittest.main()