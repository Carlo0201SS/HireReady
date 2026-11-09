import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from backend.domain.models.cv_model import CVParsedProfile
from backend.domain.models.interview_model import HireReadyTurn
from backend.controller import _rebuild_state
from backend.manager.llm.gemma_interview import (
    DOMANDE_CV,
    DOMANDE_TECNICHE,
    GemmaInterview,
    InterviewState,
    SYSTEM_PROMPT_TEMPLATE,
    _ensure_meaningful_classification,
    _is_blocked,
    _response_schema_for_turn,
    _validate_turn_payload,
)


class InterviewModerationPolicyTests(unittest.TestCase):
    def test_system_prompt_limits_blocking_to_profanity_and_insults(self):
        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            position="Sviluppatore Python",
            position_description="Esperienza con API REST.",
            candidate_profile="{}",
            num_domande_cv=DOMANDE_CV,
            num_domande_tecniche=DOMANDE_TECNICHE,
        )
        self.assertIn("Esperienza con API REST.", prompt)

        self.assertIn('is_meaningful.azione="blocca" se lingua non è "Italiano"', prompt)
        self.assertIn("volgarità o rivolge insulti offensivi", prompt)
        self.assertIn("risposte errate, vaghe, incomplete, non pertinenti", prompt)
        self.assertIn('turn_id 0, 1 e 2: phase="cv"', prompt)
        self.assertIn("La prima chiamata avviene con turn_id=0", prompt)
        self.assertIn("la prima domanda è il turno 0", prompt)
        self.assertIn("non dire \"passiamo alla seconda domanda\"", prompt)
        self.assertIn('turn_id 3: phase="presentazione"', prompt)
        self.assertIn('turn_id da 4 a 10: phase="tecnica"', prompt)
        self.assertIn('turn_id 11: phase="finale" e is_final=true', prompt)
        self.assertIn("esattamente 7 domande", prompt)
        self.assertIn("un intero da 1 a 10", prompt)
        self.assertIn("usa esattamente \"Italiano\" se è in italiano", prompt)
        self.assertIn("esclusivamente per dare un consiglio di miglioramento breve", prompt)
        self.assertIn("Non riassumere la risposta, non spiegare il voto", prompt)
        self.assertIn("Anche per una risposta di alta qualità indica un piccolo passo pratico", prompt)
        self.assertIn(
            'Da turn_id 1 in poi è obbligatorio restituire l\'oggetto '
            'is_meaningful',
            prompt,
        )

    def test_start_generates_the_first_question_on_turn_zero(self):
        interview = GemmaInterview()
        interview._request_turn = Mock(
            return_value=(
                '{"turn_id":0,"phase":"cv","is_final":false,'
                '"is_meaningful":null,'
                '"evaluation_of_previous_answer":null,'
                '"next_question":{"id":1,'
                '"text":"Raccontami un progetto professionale rilevante."}}'
            )
        )
        profile = CVParsedProfile.model_validate(
            {
                "professional_summary": "Sviluppatore web.",
                "technical_skills": ["Python"],
                "relevant_experience": ["Sviluppo backend."],
                "education": [],
                "certifications": [],
                "interview_focus": ["API"],
            }
        )

        turn, state = interview.start(
            position="Sviluppatore backend",
            candidate_profile=profile,
            position_description="Esperienza con API REST e PostgreSQL.",
        )

        self.assertEqual(state.turn_id, 0)
        self.assertEqual(turn.turn_id, 0)
        prompt_messages = interview._request_turn.call_args.args[0]
        self.assertIn(
            "Esperienza con API REST e PostgreSQL.",
            prompt_messages[0]["content"],
        )
        self.assertIn(
            "Personalizza queste domande usando la sezione",
            prompt_messages[0]["content"],
        )
        response_format = interview._request_turn.call_args.args[1]
        self.assertEqual(
            response_format["json_schema"]["schema"]["properties"]["turn_id"][
                "const"
            ],
            0,
        )

    def test_json_schema_documents_moderation_and_finalization_rules(self):
        schema = HireReadyTurn.model_json_schema()
        properties = schema["$defs"]["IsMeaningful"]["properties"]

        self.assertIn("volgarità o insulti", properties["azione"]["description"])
        self.assertIn("lingua", properties)
        self.assertIn("Italiano", properties["lingua"]["description"])
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
                for option in cv_schema["properties"][
                    "evaluation_of_previous_answer"
                ]["anyOf"]
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
        self.assertEqual(
            final_schema["properties"]["evaluation_of_previous_answer"],
            {"type": "null"},
        )
        initial_schema = _response_schema_for_turn(0)
        self.assertTrue(
            any(
                option.get("type") == "null"
                for option in initial_schema["properties"]["is_meaningful"]["anyOf"]
            )
        )
        self.assertTrue(
            any(
                option.get("type") == "null"
                for option in initial_schema["properties"][
                    "evaluation_of_previous_answer"
                ]["anyOf"]
            )
        )

    def test_is_meaningful_is_nullable_only_on_initial_turn(self):
        initial_turn = {
            "turn_id": 0,
            "phase": "cv",
            "is_final": False,
            "is_meaningful": None,
            "evaluation_of_previous_answer": None,
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
                    "lingua": "Italiano",
                    "motivazione": "Classificazione della risposta.",
                },
                "evaluation_of_previous_answer": {"score": 7},
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
        self.assertEqual(result["is_meaningful"]["lingua"], "non determinata")

        missing_payload = {"turn_id": 4}
        result = _ensure_meaningful_classification(missing_payload, 4)
        self.assertEqual(result["is_meaningful"]["azione"], "prosegui")

        classified_payload = {
            "turn_id": 2,
            "is_meaningful": {
                "azione": "blocca",
                "lingua": "Italiano",
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
                '"evaluation_of_previous_answer":{"score":8},'
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
                        "lingua": "Italiano",
                        "motivazione": "Il linguaggio è appropriato.",
                    },
                    "evaluation_of_previous_answer": (
                        None if turn_id in (0, 11) else {"score": 7}
                    ),
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
                    "lingua": "Italiano",
                    "motivazione": "È stato usato un insulto offensivo.",
                },
                "evaluation_of_previous_answer": {"score": 1},
                "next_question": None,
            },
            context={"expected_turn_id": 2},
        )
        self.assertTrue(blocked_turn.is_final)

    def test_normal_final_turn_marks_interview_closed(self):
        final_turn = HireReadyTurn.model_validate(
            {
                "turn_id": 11,
                "phase": "finale",
                "is_final": True,
                "is_meaningful": {
                    "azione": "prosegui",
                    "lingua": "Italiano",
                    "motivazione": "Il linguaggio è appropriato.",
                },
                "evaluation_of_previous_answer": None,
                "next_question": None,
            }
        )
        previous_turn = HireReadyTurn.model_validate(
            {
                "turn_id": 10,
                "phase": "tecnica",
                "is_final": False,
                "is_meaningful": {
                    "azione": "prosegui",
                    "lingua": "Italiano",
                    "motivazione": "Il linguaggio è appropriato.",
                },
                "evaluation_of_previous_answer": {"score": 8},
                "next_question": {
                    "id": 11,
                    "text": "Descrivi un problema tecnico complesso.",
                },
            }
        )
        state = InterviewState(turn_id=10, last_turn=previous_turn)
        interview = GemmaInterview()

        with patch.object(interview, "_call_llm", return_value=final_turn):
            turn = interview.next_turn(
                state=state,
                candidate_answer="Ho risolto un problema tecnico.",
            )

        self.assertTrue(turn.is_final)
        self.assertTrue(state.is_closed)

    def test_moderation_close_marks_interview_closed(self):
        blocked_turn = HireReadyTurn.model_validate(
            {
                "turn_id": 4,
                "phase": "tecnica",
                "is_final": False,
                "is_meaningful": {
                    "azione": "blocca",
                    "lingua": "Italiano",
                    "motivazione": "Linguaggio offensivo.",
                },
                "evaluation_of_previous_answer": {"score": 1},
                "next_question": {
                    "id": 5,
                    "text": "Descrivi un progetto tecnico.",
                },
            }
        )
        previous_turn = HireReadyTurn.model_validate(
            {
                "turn_id": 3,
                "phase": "presentazione",
                "is_final": False,
                "is_meaningful": {
                    "azione": "prosegui",
                    "lingua": "Italiano",
                    "motivazione": "Il linguaggio è appropriato.",
                },
                "evaluation_of_previous_answer": {"score": 8},
                "next_question": {
                    "id": 4,
                    "text": "Come si relazionano le tue competenze al ruolo?",
                },
            }
        )
        state = InterviewState(turn_id=3, last_turn=previous_turn)
        interview = GemmaInterview()

        with patch.object(interview, "_call_llm", return_value=blocked_turn):
            turn = interview.next_turn(
                state=state,
                candidate_answer="Risposta con linguaggio offensivo.",
            )

        self.assertTrue(turn.is_final)
        self.assertTrue(state.is_closed)

    def test_non_italian_answer_forces_interview_close(self):
        turn = HireReadyTurn.model_validate(
            {
                "turn_id": 4,
                "phase": "tecnica",
                "is_final": False,
                "is_meaningful": {
                    "azione": "prosegui",
                    "lingua": "Inglese",
                    "motivazione": "Migliora la specificità della risposta.",
                },
                "evaluation_of_previous_answer": {"score": 7},
                "next_question": {
                    "id": 5,
                    "text": "Descrivi un progetto tecnico.",
                },
            }
        )

        self.assertTrue(_is_blocked(turn))
        closed_turn = GemmaInterview._force_close_turn(turn)

        self.assertTrue(closed_turn.is_final)
        self.assertEqual(closed_turn.phase, "finale")
        self.assertIsNone(closed_turn.next_question)
        self.assertEqual(closed_turn.is_meaningful.azione, "blocca")
        self.assertIn("solo in italiano", closed_turn.is_meaningful.motivazione)

    def test_rebuilt_state_is_closed_for_final_or_blocked_turn(self):
        final_turn = HireReadyTurn.model_validate(
            {
                "turn_id": 11,
                "phase": "finale",
                "is_final": True,
                "is_meaningful": {
                    "azione": "prosegui",
                    "lingua": "Italiano",
                    "motivazione": "Il linguaggio è appropriato.",
                },
                "evaluation_of_previous_answer": None,
                "next_question": None,
            }
        )
        blocked_turn = HireReadyTurn.model_validate(
            {
                "turn_id": 4,
                "phase": "finale",
                "is_final": True,
                "is_meaningful": {
                    "azione": "blocca",
                    "lingua": "Italiano",
                    "motivazione": "Linguaggio offensivo.",
                },
                "evaluation_of_previous_answer": {"score": 1},
                "next_question": None,
            }
        )

        for last_turn in (final_turn, blocked_turn):
            with self.subTest(turn_id=last_turn.turn_id):
                state = _rebuild_state([], last_turn)
                self.assertTrue(state.is_closed)

    def test_rejects_phase_mismatch_and_unexpected_turn_id(self):
        turn = {
            "turn_id": 3,
            "phase": "cv",
            "is_final": False,
            "is_meaningful": {
                "azione": "prosegui",
                "lingua": "Italiano",
                "motivazione": "Il linguaggio è appropriato.",
            },
            "evaluation_of_previous_answer": {"score": 7},
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
