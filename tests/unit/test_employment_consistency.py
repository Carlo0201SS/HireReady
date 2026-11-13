import json
import unittest
from unittest.mock import Mock, patch

from backend.domain.models.interview_model import ProfileConsistencyCheck, HireReadyTurn
from backend.manager.llm.gemma_interview import (
	GemmaInterview,
	InterviewState,
	_response_schema_for_turn,
)


class EmploymentConsistencyTests(unittest.TestCase):
	def setUp(self):
		self.system_prompt = (
			"# PROFILO DEL CANDIDATO\n"
			'{"relevant_experience":["Dal 2019 al 2021 ho lavorato per XYZ."]}'
			"\n\n# NOME."
		)

	def test_detects_conflicting_employer_for_same_period_with_exact_evidence(self):
		client = Mock()
		client.chat_completions.return_value = (
			200,
			json.dumps(
				{
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"status": "contradiction",
										"current_claim": (
											"Dal 2019 al 2021 ho lavorato per ABC."
										),
										"conflicting_claim": (
											"Dal 2019 al 2021 ho lavorato per XYZ."
										),
									}
								)
							}
						}
					]
				}
			),
		)
		interview = GemmaInterview(lm_studio=client, model="test")
		state = InterviewState(
			anonymized_cv="Esperienza: Dal 2019 al 2021 ho lavorato per XYZ.",
			history=[
				{"role": "system", "content": self.system_prompt},
				{"role": "user", "content": "Dal 2019 al 2021 ho lavorato per XYZ."},
			]
		)

		result = interview._check_profile_consistency(
			state=state,
			candidate_answer="Dal 2019 al 2021 ho lavorato per ABC.",
		)

		self.assertEqual(result.status, "contradiction")
		self.assertIn(
			"previous_candidate_answers",
			client.chat_completions.call_args.args[1][1]["content"],
		)

	def test_ignores_contradiction_without_verifiable_quotes(self):
		client = Mock()
		client.chat_completions.return_value = (
			200,
			json.dumps(
				{
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"status": "contradiction",
										"current_claim": "Ho lavorato per ABC nel 2020.",
										"conflicting_claim": (
											"XYZ era il mio datore di lavoro nel 2019."
										),
									}
								)
							}
						}
					]
				}
			),
		)
		interview = GemmaInterview(lm_studio=client, model="test")
		state = InterviewState(
			anonymized_cv="Esperienza: Dal 2019 al 2021 ho lavorato per XYZ.",
			history=[
				{"role": "system", "content": self.system_prompt},
				{"role": "user", "content": "Ho lavorato per XYZ nel 2020."},
			]
		)

		result = interview._check_profile_consistency(
			state=state,
			candidate_answer="Ho lavorato per ABC nel 2020.",
		)

		self.assertEqual(result.status, "consistent")

	def test_closes_early_on_verified_contradiction(self):
		questioned_turn = HireReadyTurn.model_validate(
			{
				"turn_id": 4,
				"phase": "tecnica",
				"is_final": False,
				"is_meaningful": {
					"azione": "prosegui",
					"lingua": "Italiano",
					"motivazione": "Aggiungi dettagli.",
				},
				"evaluation_of_previous_answer": {"score": 7},
				"next_question": {
					"id": 5,
					"text": "Descrivi un progetto tecnico rilevante.",
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
					"motivazione": "Aggiungi dettagli.",
				},
				"evaluation_of_previous_answer": {"score": 7},
				"next_question": {
					"id": 4,
					"text": "Quali sono le tue competenze principali?",
				},
			}
		)
		state = InterviewState(
			turn_id=3,
			history=[
				{"role": "system", "content": self.system_prompt},
				{"role": "user", "content": "Dal 2019 al 2021 ho lavorato per XYZ."},
			],
			last_turn=previous_turn,
		)
		interview = GemmaInterview(lm_studio=Mock(), model="test")
		check = ProfileConsistencyCheck(
			status="contradiction",
			current_claim="Dal 2019 al 2021 ho lavorato per ABC.",
			conflicting_claim="Dal 2019 al 2021 ho lavorato per XYZ.",
		)

		with (
			patch.object(
				interview,
				"_request_turn",
				return_value=questioned_turn.model_dump_json(),
			),
			patch.object(interview, "_check_profile_consistency", return_value=check) as check_mock,
		):
			turn = interview.next_turn(
				state=state,
				candidate_answer="Dal 2019 al 2021 ho lavorato per ABC.",
			)

		self.assertTrue(turn.is_final)
		self.assertTrue(state.is_closed)
		self.assertEqual(turn.phase, "finale")
		self.assertIsNone(turn.next_question)
		self.assertEqual(turn.closure_reason, "profile_contradiction")
		self.assertEqual(len(turn.closure_evidence), 2)
		self.assertEqual(
			HireReadyTurn.model_validate(turn.model_dump()).closure_reason,
			"profile_contradiction",
		)
		check_mock.assert_called_once_with(
			state=state,
			candidate_answer="Dal 2019 al 2021 ho lavorato per ABC.",
		)
		self.assertNotIn(
			"Descrivi un progetto tecnico rilevante.",
			[message["content"] for message in state.history],
		)
		self.assertNotIn("closure_reason", _response_schema_for_turn(4)["properties"])

	def test_detects_denial_of_cv_skill_without_requiring_dates(self):
		client = Mock()
		client.chat_completions.return_value = (
			200,
			json.dumps(
				{
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"status": "contradiction",
										"current_claim": "non l'ho mai utilizzato",
										"conflicting_claim": "Django",
									}
								)
							}
						}
					]
				}
			),
		)
		profile_prompt = (
			"# PROFILO DEL CANDIDATO\n"
			'{"technical_skills":["Django"]}'
			"\n\n# NOME."
		)
		state = InterviewState(
			anonymized_cv="Competenze: Django",
			history=[
				{"role": "system", "content": profile_prompt},
				{"role": "assistant", "content": "Hai mai usato Django?"},
				{"role": "user", "content": "Ho lavorato con Python."},
				{"role": "user", "content": "In realtà non l'ho mai utilizzato."},
				{"role": "user", "content": "In realtà non l'ho mai utilizzato."},
			]
		)
		interview = GemmaInterview(lm_studio=client, model="test")

		result = interview._check_profile_consistency(
			state=state,
			candidate_answer="In realtà non l'ho mai utilizzato.",
		)

		self.assertEqual(result.status, "contradiction")
		request = json.loads(client.chat_completions.call_args.args[1][1]["content"])
		self.assertEqual(
			request,
			{
				"anonymized_cv": "Competenze: Django",
				"previous_candidate_answers": [
					"Ho lavorato con Python.",
					"In realtà non l'ho mai utilizzato.",
				],
				"current_candidate_answer": "In realtà non l'ho mai utilizzato.",
			},
		)

	def test_checks_even_when_no_profile_fields_or_date_pattern_trigger_a_match(self):
		client = Mock()
		client.chat_completions.return_value = (
			200,
			json.dumps(
				{
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"status": "consistent",
										"current_claim": "",
										"conflicting_claim": "",
									}
								)
							}
						}
					]
				}
			),
		)
		state = InterviewState(
			anonymized_cv="CV [PERSON] con competenze non indicate.",
			history=[
				{
					"role": "system",
					"content": (
						"# PROFILO DEL CANDIDATO\n"
						'{"technical_skills":[],"education":[]}'
						"\n\n# NOME."
					),
				}
			]
		)
		interview = GemmaInterview(lm_studio=client, model="test")

		result = interview._check_profile_consistency(
			state=state,
			candidate_answer="Non ho mai utilizzato Django.",
		)

		self.assertEqual(result.status, "consistent")
		client.chat_completions.assert_called_once()

	def test_allows_candidate_to_add_details_missing_from_cv_summary(self):
		client = Mock()
		client.chat_completions.return_value = (
			200,
			json.dumps(
				{
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"status": "consistent",
										"current_claim": "",
										"conflicting_claim": "",
									}
								)
							}
						}
					]
				}
			),
		)
		interview = GemmaInterview(lm_studio=client, model="test")
		cv_summary = "Sviluppatore frontend presso Acme."
		candidate_answer = (
			"Presso Acme ho seguito il redesign del portale, implementando "
			"componenti React e test automatici."
		)

		result = interview._check_profile_consistency(
			state=InterviewState(anonymized_cv=cv_summary),
			candidate_answer=candidate_answer,
		)

		self.assertEqual(result.status, "consistent")
		prompt = client.chat_completions.call_args.args[1][0]["content"]
		self.assertIn("dettagli aggiuntivi", prompt)
		self.assertIn("NON sono contraddizioni", prompt)
		self.assertIn("In caso di dubbio o ambiguità usa 'consistent'", prompt)

	def test_checks_education_certification_and_relevant_experience_claims(self):
		cases = (
			(
				"education",
				"Laurea in Informatica conseguita presso l'Università XYZ.",
				"Non ho conseguito una laurea in Informatica.",
				"Laurea in Informatica conseguita presso l'Università XYZ.",
			),
			(
				"certifications",
				"Certificazione AWS Certified Developer.",
				"Non possiedo la certificazione AWS Certified Developer.",
				"Certificazione AWS Certified Developer.",
			),
			(
				"relevant_experience",
				"Ho svolto un progetto di migrazione cloud per Acme.",
				"Non ho mai svolto un progetto di migrazione cloud per Acme.",
				"Ho svolto un progetto di migrazione cloud per Acme.",
			),
		)

		for field, profile_claim, answer, expected_conflicting_claim in cases:
			with self.subTest(field=field):
				client = Mock()
				client.chat_completions.return_value = (
					200,
					json.dumps(
						{
							"choices": [
								{
									"message": {
										"content": json.dumps(
											{
												"status": "contradiction",
												"current_claim": answer,
												"conflicting_claim": expected_conflicting_claim,
											}
										)
									}
								}
							]
						}
					),
				)
				profile_prompt = (
					"# PROFILO DEL CANDIDATO\n"
					+ json.dumps({field: [profile_claim]}, ensure_ascii=False)
					+ "\n\n# NOME."
				)
				interview = GemmaInterview(lm_studio=client, model="test")
				result = interview._check_profile_consistency(
					state=InterviewState(
						anonymized_cv=profile_claim,
						history=[{"role": "system", "content": profile_prompt}],
					),
					candidate_answer=answer,
				)

				self.assertEqual(result.status, "contradiction")
				self.assertEqual(result.conflicting_claim, expected_conflicting_claim)
				client.chat_completions.assert_called_once()

	def test_detects_conflicting_identity_from_anonymized_cv(self):
		client = Mock()
		client.chat_completions.return_value = (
			200,
			json.dumps(
				{
					"choices": [
						{
							"message": {
								"content": json.dumps(
									{
										"status": "contradiction",
										"current_claim": (
											"Io mi chiamo Gabriele Grandi."
										),
										"conflicting_claim": "Giuseppe Landi",
									}
								)
							}
						}
					]
				}
			),
		)
		interview = GemmaInterview(lm_studio=client, model="test")
		state = InterviewState(
			anonymized_cv="Nome: Giuseppe Landi",
			history=[{"role": "system", "content": "Prompt non rilevante"}],
		)

		result = interview._check_profile_consistency(
			state=state,
			candidate_answer="Io mi chiamo Gabriele Grandi.",
		)

		self.assertEqual(result.status, "contradiction")
		request = json.loads(client.chat_completions.call_args.args[1][1]["content"])
		self.assertEqual(request["anonymized_cv"], "Nome: Giuseppe Landi")
		self.assertEqual(
			set(request),
			{
				"anonymized_cv",
				"previous_candidate_answers",
				"current_candidate_answer",
			},
		)
		prompt = client.chat_completions.call_args.args[1][0]["content"]
		self.assertIn(
			"Usa 'contradiction' esclusivamente quando le due affermazioni",
			prompt,
		)
		self.assertIn("dichiarare un nome diverso", prompt)


if __name__ == "__main__":
	unittest.main()
