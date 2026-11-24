from typing import Protocol

from backend.domain.models.cv_model import CVParserResult


class CVParser(Protocol):
	def parse(
		self,
		anonymized_cv: str,
		selected_position: str,
		position_description: str = "",
	) -> CVParserResult: ...
