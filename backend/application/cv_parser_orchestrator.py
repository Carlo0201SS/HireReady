from backend.domain.models.cv_model import CVInterviewContext
from backend.domain.ports.cv_parser import CVParser


class CVParserOrchestrator:
	def __init__(self, parser: CVParser) -> None:
		self._parser = parser

	def parse_for_interview(
		self,
		*,
		anonymized_cv: str,
		selected_position: str,
	) -> CVInterviewContext:
		if not anonymized_cv.strip():
			raise ValueError("Il CV anonimizzato è vuoto.")
		if not selected_position.strip():
			raise ValueError("La posizione selezionata è vuota.")

		profile = self._parser.parse(anonymized_cv, selected_position)
		return CVInterviewContext(
			selected_position=selected_position,
			profile=profile,
		)