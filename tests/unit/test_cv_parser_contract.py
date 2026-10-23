import unittest
from unittest.mock import Mock, patch
import json

from pydantic import ValidationError

from backend.application.cv_parser_orchestrator import CVParserOrchestrator
from backend.domain.models.api import CVParserRequest
from backend.domain.models.cv import CVInterviewContext, CVParsedProfile
from HireReady.backend.manager.llm.gemma_cv_parser import GemmaCVParser


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
	@patch("backend.infrastructure.llm.gemma_cv_parser.requests.post")
	def test_sends_anonymized_cv_and_position_with_json_schema(self, post):
		response = Mock(ok=True)
		response.json.return_value = {
			"choices": [{"message": {"content": json.dumps(PROFILE)}}],
		}
		post.return_value = response
		parser = GemmaCVParser(
			base_url="http://localhost:1234/v1",
			model="google/gemma-4-e2b",
			api_key="test-key",
		)

		profile = parser.parse("CV [EMAIL]", "Sviluppatore web React")

		self.assertEqual(profile.technical_skills, ["React", "TypeScript"])
		kwargs = post.call_args.kwargs
		self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
		messages = kwargs["json"]["messages"]
		self.assertIn("CV [EMAIL]", messages[1]["content"])
		self.assertIn("Sviluppatore web React", messages[1]["content"])
		self.assertEqual(
			kwargs["json"]["response_format"]["json_schema"]["schema"],
			CVParsedProfile.model_json_schema(),
		)

	@patch("backend.infrastructure.llm.gemma_cv_parser.requests.post")
	def test_rejects_nonconforming_model_output(self, post):
		response = Mock(ok=True)
		response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
		post.return_value = response
		parser = GemmaCVParser()

		with self.assertRaisesRegex(RuntimeError, "non conforme allo schema"):
			parser.parse("CV anonimizzato", "ML Engineer")


if __name__ == "__main__":
	 unittest.main()