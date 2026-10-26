from typing import Protocol

from backend.domain.models.cv_model import CVParsedProfile


class CVParser(Protocol):
	def parse(self, anonymized_cv: str, selected_position: str) -> CVParsedProfile: ...
