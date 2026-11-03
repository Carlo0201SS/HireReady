import unittest

from pydantic import ValidationError

from backend.domain.models.interview_model import HireReadyTurn
from backend.manager.llm.gemma_interview import (
    DOMANDE_CV,
    DOMANDE_TECNICHE,
    SYSTEM_PROMPT_TEMPLATE,
    _ensure_meaningful_classification,
    _response_schema_for_turn,
    _validate_turn_payload,
)


class InterviewModerationPolicyTests(unittest.TestCase):
    def test_system_prompt_limits_blocking_to_profanity_and_insults(self):
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            position="Sviluppatore Python",
            candidate_profile="{}",
            num_domande_cv=DOMANDE_CV,
            num_domande_tecniche=DOMANDE_TECNICHE,
        )

        self.assertIn('is_meaningful.azione="blocca" esclusivamente', prompt)
        self.assertIn("volgarità o rivolge insulti offensivi", prompt)
        self.assertIn("risposte errate, vaghe, incomplete, non pertinenti", prompt)
        self.assertIn('turn_id 0, 1 e 2: phase="cv"', prompt)
        self.assertIn('turn_id 3: phase="presentazione"', prompt)
        self.assertIn('turn_id da 4 a 10: phase="tecnica"', prompt)
        self.assertIn('turn_id 11: phase="finale" e is_final=true', prompt)
        self.assertIn("esattamente 7 domande", prompt)
        self.assertIn(
            'Da turn_id 1 in poi è obbligatorio restituire l\'oggetto '
            'is_meaningful',
            prompt,
        )

    def test_json_schema_documents_moderation_and_finalization_rules(self):
        schema = HireReadyTurn.model_json_schema()
        properties = schema["$defs"]["IsMeaningful"]["properties"]

        self.assertIn("volgarità o insulti", properties["azione"]["description"])
        self.assertIn("risposte errate, vaghe o non pertinenti", schema["properties"]["is_final"]["description"])

    def test_turn_schema_is_specialized_to_the_expected_id_and_phase(self):
        cv_schema = _response_schema_for_turn(2)
        final_schema = _response_schema_for_turn(11)

        self.assertEqual(cv_schema["properties"]["turn_id"]["const"], 2)
        self.assertEqual(cv_schema["properties"]["phase"]["const"], "cv")
        self.assertIs(cv_schema["properties"]["is_final"]["const"], False)
        self.assertTrue(
            all(
                option.get("type") != "null"
                for option in cv_schema["properties"]["is_meaningful"]["anyOf"]
            )
        )
        self.assertTrue(
            all(
                option.get("type") != "null"
                for option in cv_schema["properties"]["next_question"]["anyOf"]
            )
        )
        self.assertEqual(final_schema["properties"]["phase"]["const"], "finale")
        self.assertIs(final_schema["properties"]["is_final"]["const"], True)
        self.assertEqual(
            final_schema["properties"]["next_question"],
            {"type": "null"},
        )
        initial_schema = _response_schema_for_turn(0)
        self.assertTrue(
            any(
                option.get("type") == "null"
                for option in initial_schema["properties"]["is_meaningful"]["anyOf"]
            )
        )

    def test_is_meaningful_is_nullable_only_on_initial_turn(self):
        initial_turn = {
            "turn_id": 0,
            "phase": "cv",
            "is_final": False,
            "is_meaningful": None,
            "next_question": {
                "id": 1,
                "text": "Raccontami un'esperienza professionale.",
            },
        }
        HireReadyTurn.model_validate(initial_turn)

        for action in ("prosegui", "blocca"):
            turn = {
                **initial_turn,
                "turn_id": 1,
                "is_meaningful": {
                    "azione": action,
                    "motivazione": "Classificazione della risposta.",
                },
                "next_question": {
                    "id": 2,
                    "text": "Quali strumenti hai utilizzato?",
                },
            }
            HireReadyTurn.model_validate(turn)

        invalid_turn = {
            **initial_turn,
            "turn_id": 1,
        }
        with self.assertRaises(ValidationError):
            HireReadyTurn.model_validate(invalid_turn)

        missing_classification = {
            **initial_turn,
            "turn_id": 1,
        }
        del missing_classification["is_meaningful"]
        with self.assertRaises(ValidationError):
            HireReadyTurn.model_validate(missing_classification)

    def test_missing_classification_defaults_to_continue_only_after_start(self):
        initial_payload = {
            "turn_id": 0,
            "is_meaningful": None,
        }
        self.assertIs(
            _ensure_meaningful_classification(initial_payload, 0),
            initial_payload,
        )

        payload = {"turn_id": 3, "is_meaningful": None}
        result = _ensure_meaningful_classification(payload, 3)
        self.assertEqual(result["is_meaningful"]["azione"], "prosegui")
        self.assertIn(
            "non è stato identificato con certezza",
            result["is_meaningful"]["motivazione"],
        )

        missing_payload = {"turn_id": 4}
        result = _ensure_meaningful_classification(missing_payload, 4)
        self.assertEqual(result["is_meaningful"]["azione"], "prosegui")

        classified_payload = {
            "turn_id": 2,
            "is_meaningful": {
                "azione": "blocca",
                "motivazione": "Insulto offensivo.",
            },
        }
        self.assertIs(
            _ensure_meaningful_classification(classified_payload, 2),
            classified_payload,
        )

    def test_turn_payload_validation_applies_safe_classification_fallback(self):
        turn = _validate_turn_payload(
            (
                '{"turn_id":3,"phase":"presentazione","is_final":false,'
                '"is_meaningful":null,'
                '"next_question":{"id":4,'
                '"text":"Raccontami il tuo percorso professionale."}}'
            ),
            3,
        )

        self.assertIsNotNone(turn.is_meaningful)
        assert turn.is_meaningful is not None
        self.assertEqual(turn.is_meaningful.azione, "prosegui")

    def test_turn_id_phase_schedule_and_early_moderation_close(self):
        schedule = {
            **{turn_id: "cv" for turn_id in range(0, 3)},
            3: "presentazione",
            **{turn_id: "tecnica" for turn_id in range(4, 11)},
            11: "finale",
        }

        for turn_id, phase in schedule.items():
            is_final = turn_id == 11
            turn = HireReadyTurn.model_validate(
                {
                    "turn_id": turn_id,
                    "phase": phase,
                    "is_final": is_final,
                    "is_meaningful": {
                        "azione": "prosegui",
                        "motivazione": "Il linguaggio è appropriato.",
                    },
                    "next_question": (
                        None
                        if is_final
                        else {
                            "id": turn_id + 1,
                            "text": "Raccontami un'esperienza professionale.",
                        }
                    ),
                },
                context={"expected_turn_id": turn_id},
            )
            self.assertEqual(turn.phase, phase)

        blocked_turn = HireReadyTurn.model_validate(
            {
                "turn_id": 2,
                "phase": "finale",
                "is_final": True,
                "is_meaningful": {
                    "azione": "blocca",
                    "motivazione": "È stato usato un insulto offensivo.",
                },
                "next_question": None,
            },
            context={"expected_turn_id": 2},
        )
        self.assertTrue(blocked_turn.is_final)

    def test_rejects_phase_mismatch_and_unexpected_turn_id(self):
        turn = {
            "turn_id": 3,
            "phase": "cv",
            "is_final": False,
            "is_meaningful": {
                "azione": "prosegui",
                "motivazione": "Il linguaggio è appropriato.",
            },
            "next_question": {
                "id": 4,
                "text": "Raccontami un'esperienza professionale.",
            },
        }

        with self.assertRaises(ValidationError):
            HireReadyTurn.model_validate(turn)

        turn["phase"] = "presentazione"
        with self.assertRaises(ValidationError):
            HireReadyTurn.model_validate(
                turn,
                context={"expected_turn_id": 2},
            )


if __name__ == "__main__":
    unittest.main()
