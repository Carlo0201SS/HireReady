import unittest

from pydantic import ValidationError

from backend.domain.models.interview_model import HireReadyTurn


START_TURN = {
	"turn_id": 0,
	"phase": "cv",
	"is_final": False,
	"is_meaningful": None,
	"evaluation_of_previous_answer": None,
	"next_question": {
		"id": 1,
		"text": "Raccontami le esperienze più rilevanti del tuo percorso.",
	},
}


FINAL_TURN = {
	"turn_id": 11,
	"phase": "finale",
	"is_final": True,
	"is_meaningful": {
		"azione": "prosegui",
		"motivazione": "Il linguaggio è appropriato.",
	},
	"evaluation_of_previous_answer": None,
	"next_question": None,
}


class InterviewSchemaTests(unittest.TestCase):
	def test_validates_start_turn_and_generates_json_schema(self):
		turn = HireReadyTurn.model_validate(START_TURN)
		schema = HireReadyTurn.model_json_schema()

		self.assertEqual(turn.turn_id, 0)
		self.assertIn("evaluation_of_previous_answer", schema["properties"])
		self.assertIn(
			"score",
			schema["$defs"]["EvaluationOfPreviousAnswer"]["properties"],
		)

	def test_validates_final_turn_without_score(self):
		turn = HireReadyTurn.model_validate(FINAL_TURN)

		self.assertTrue(turn.is_final)
		self.assertIsNone(turn.evaluation_of_previous_answer)

	def test_requires_score_for_every_turn_after_start(self):
		turn = {
			**FINAL_TURN,
			"turn_id": 3,
			"phase": "presentazione",
			"is_final": False,
			"next_question": {
				"id": 4,
				"text": "Raccontami il tuo percorso professionale.",
			},
			"evaluation_of_previous_answer": None,
		}

		with self.assertRaises(ValidationError):
			HireReadyTurn.model_validate(turn)

	def test_rejects_scores_outside_one_to_ten(self):
		for score in (0, 11):
			with self.subTest(score=score):
				turn = {
					**FINAL_TURN,
					"evaluation_of_previous_answer": {"score": score},
				}
				with self.assertRaises(ValidationError):
					HireReadyTurn.model_validate(turn)

	def test_final_turn_rejects_a_score(self):
		with self.assertRaises(ValidationError):
			HireReadyTurn.model_validate(
				{
					**FINAL_TURN,
					"evaluation_of_previous_answer": {"score": 8},
				}
			)

	def test_validates_early_moderation_close(self):
		turn = {
			"turn_id": 1,
			"phase": "finale",
			"is_final": True,
			"is_meaningful": {
				"azione": "blocca",
				"motivazione": "Risposta offensiva.",
			},
			"evaluation_of_previous_answer": {"score": 1},
			"next_question": None,
		}

		self.assertTrue(HireReadyTurn.model_validate(turn).is_final)


if __name__ == "__main__":
	unittest.main()
