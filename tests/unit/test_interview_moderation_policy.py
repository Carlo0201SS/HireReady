import unittest

from backend.domain.models.interview_model import HireReadyTurn
from backend.manager.llm.gemma_interview import SYSTEM_PROMPT_TEMPLATE


class InterviewModerationPolicyTests(unittest.TestCase):
    def test_system_prompt_limits_blocking_to_profanity_and_insults(self):
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            position="Sviluppatore Python",
            candidate_profile="{}",
            num_domande_tecniche=5,
        )

        self.assertIn('is_meaningful.azione="blocca" esclusivamente', prompt)
        self.assertIn("volgarità o rivolge insulti offensivi", prompt)
        self.assertIn("risposte errate, vaghe, incomplete, non pertinenti", prompt)
        self.assertIn("is_final indica solo la normale conclusione", prompt)

    def test_json_schema_documents_moderation_and_finalization_rules(self):
        schema = HireReadyTurn.model_json_schema()
        properties = schema["$defs"]["IsMeaningful"]["properties"]

        self.assertIn("volgarità o insulti", properties["azione"]["description"])
        self.assertIn("risposte errate, vaghe o non pertinenti", schema["properties"]["is_final"]["description"])


if __name__ == "__main__":
    unittest.main()
