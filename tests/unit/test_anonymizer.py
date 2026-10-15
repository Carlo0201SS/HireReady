import unittest
from unittest.mock import Mock, patch

from src.infrastructure.cv.rizzo_anonymizer import RizzoAnonymizer


class RizzoAnonymizerTests(unittest.TestCase):
	def test_replaces_detected_entities_with_labels(self):
		text = "Ada Lovelace, ada@example.com"
		entities = [
			{"start": 0, "end": len("Ada Lovelace"), "entity_group": "PERSON"},
			{
				"start": text.index("ada@example.com"),
				"end": text.index("ada@example.com") + len("ada@example.com"),
				"entity_group": "EMAIL",
			},
		]
		anonymizer = RizzoAnonymizer()

		with patch.object(anonymizer, "_get_pipeline", return_value=Mock(return_value=entities)):
			result = anonymizer.anonymize(text)

		self.assertEqual(result, "[PERSON], [EMAIL]")

	def test_empty_text_does_not_load_the_model(self):
		anonymizer = RizzoAnonymizer()

		with patch.object(anonymizer, "_get_pipeline") as get_pipeline:
			self.assertEqual(anonymizer.anonymize(""), "")

		get_pipeline.assert_not_called()

	def test_redacts_contacts_grades_and_social_links_but_keeps_github(self):
		text = (
			"Email: ada@example.com; telefono: +39 333 123 4567; "
			"voto 30/30; LinkedIn: https://www.linkedin.com/in/ada; "
			"GitHub: https://github.com/ada"
		)
		github_url = "https://github.com/ada"
		entities = [
			{
				"start": text.index(github_url),
				"end": text.index(github_url) + len(github_url),
				"entity_group": "URL",
			}
		]
		anonymizer = RizzoAnonymizer()

		with patch.object(anonymizer, "_get_pipeline", return_value=Mock(return_value=entities)):
			result = anonymizer.anonymize(text)

		self.assertEqual(
			result,
			"Email: [EMAIL]; telefono: [PHONE]; [GRADE]; "
			"LinkedIn: [SOCIAL_LINK]; GitHub: https://github.com/ada",
		)

	def test_normalizes_city_region_and_company_labels(self):
		text = "Milano, Lombardia, Acme S.p.A."
		entities = []
		for value, label in (
			("Milano", "CITY"),
			("Lombardia", "REGION"),
			("Acme S.p.A.", "ORG"),
		):
			start = text.index(value)
			entities.append({"start": start, "end": start + len(value), "entity_group": label})

		anonymizer = RizzoAnonymizer()
		with patch.object(anonymizer, "_get_pipeline", return_value=Mock(return_value=entities)):
			result = anonymizer.anonymize(text)

		self.assertEqual(result, "[LOCATION], [LOCATION], [COMPANY]")

	def test_ignores_zip_code_entities(self):
		text = "Anni: 1999-2022-2023-2000; fuori intervallo: 1899, 2031"
		values = ("1999-2022-2023-2000", "1899", "2031")
		entities = [
			{
				"start": text.index(value),
				"end": text.index(value) + len(value),
				"entity_group": "ZIP_CODE",
			}
			for value in values
		]
		anonymizer = RizzoAnonymizer()

		with patch.object(anonymizer, "_get_pipeline", return_value=Mock(return_value=entities)):
			result = anonymizer.anonymize(text)

		self.assertEqual(result, text)

	def test_year_sequences_are_not_detected_as_phone_numbers(self):
		text = "Anni: 1999-2022-2023"
		anonymizer = RizzoAnonymizer()

		with patch.object(anonymizer, "_get_pipeline", return_value=Mock(return_value=[])):
			result = anonymizer.anonymize(text)

		self.assertEqual(result, text)


if __name__ == "__main__":
	unittest.main()
