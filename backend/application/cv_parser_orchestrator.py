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
		position_description: str = "",
	) -> CVInterviewContext:
		if not anonymized_cv.strip():
			raise ValueError("Il CV anonimizzato è vuoto.")
		if not selected_position.strip():
			raise ValueError("La posizione selezionata è vuota.")

		result = self._parser.parse(
			anonymized_cv,
			selected_position,
			position_description,
		)
		if position_description.strip() and not result.position_description_coherent:
			raise ValueError(
				"La descrizione inserita non sembra coerente con la posizione selezionata. "
				"Modificala o rimuovila prima di continuare."
			)

		return CVInterviewContext(
			selected_position=selected_position,
			position_description=position_description,
			anonymized_cv=anonymized_cv,
			profile=result.profile,
		)