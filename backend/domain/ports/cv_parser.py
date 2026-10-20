from typing import Protocol

from backend.domain.models.cv import CVParsedProfile


class CVParser(Protocol):
	def parse(self, anonymized_cv: str, selected_position: str) -> CVParsedProfile: ...
