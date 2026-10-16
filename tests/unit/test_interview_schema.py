import unittest

from pydantic import ValidationError

from backend.domain.models.interview import InterviewStartTurn, InterviewTurn


START_TURN = {
	"turn_id": 0,
	"phase": "presentazione",
	"is_final": False,
	"is_meaningful": {
		"inappropriatezza": 1,
		"azione": "prosegui",
		"motivazione": "Inizio del colloquio.",
	},
	"evaluation_of_previous_answer": None,
	"next_question": {
		"id": 1,
		"text": "Raccontami le esperienze più rilevanti del tuo percorso.",
		"difficulty": "base",
	},
	"final_report": None,
}


FINAL_TURN = {
	"turn_id": 1,
	"phase": "finale",
	"is_final": True,
	"is_meaningful": {
		"inappropriatezza": 1,
		"azione": "prosegui",
		"motivazione": "La risposta e' pertinente.",
	},
	"evaluation_of_previous_answer": {
		"question_id": 1,
		"score": 8.0,
		"radar": {
			"chiarezza": 8.0,
			"pertinenza": 8.0,
			"esempi_concreti": 7.0,
			"correttezza_tecnica": 8.0,
		},
		"comment": "Risposta chiara.",
		"better_answer_example": "Aggiungere un esempio misurabile.",
	},
	"next_question": None,
	"final_report": {
		"total_score": 8.0,
		"radar_scores": {
			"chiarezza": 8.0,
			"pertinenza": 8.0,
			"esempi_concreti": 7.0,
			"correttezza_tecnica": 8.0,
			"comunicazione": 8.0,
		},
		"strengths": ["Chiara", "Concreta", "Preparata"],
		"improvements": ["Approfondire", "Quantificare", "Sintetizzare"],
		"seniority_fit": "adeguato",
		"next_steps": ["Rivedere i progetti", "Preparare esempi"],
		"questions_to_ask": ["Prima", "Seconda", "Terza", "Quarta", "Quinta"],
	},
}


class InterviewSchemaTests(unittest.TestCase):
	def test_validates_start_turn_and_generates_json_schema(self):
		turn = InterviewStartTurn.model_validate(START_TURN)
		schema = InterviewStartTurn.model_json_schema()

		self.assertEqual(turn.turn_id, 0)
		self.assertIn("next_question", schema["properties"])

	def test_validates_final_turn_contract(self):
		turn = InterviewTurn.model_validate(FINAL_TURN)
		schema = InterviewTurn.model_json_schema()

		self.assertTrue(turn.is_final)
		self.assertEqual(len(turn.final_report.questions_to_ask), 5)
		self.assertIn("final_report", schema["properties"])

	def test_rejects_blocked_turn_that_is_not_final(self):
		invalid_turn = {
			**FINAL_TURN,
			"phase": "tecnica",
			"is_final": False,
			"is_meaningful": {
				"inappropriatezza": 3,
				"azione": "blocca",
				"motivazione": "Risposta offensiva.",
			},
			"next_question": {**START_TURN["next_question"], "id": 2},
			"final_report": None,
		}

		with self.assertRaises(ValidationError):
			InterviewTurn.model_validate(invalid_turn)


if __name__ == "__main__":
	 unittest.main()