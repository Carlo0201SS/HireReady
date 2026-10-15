from typing import Protocol


class Anonymizer(Protocol):
	@property
	def is_available(self) -> bool: ...

	def anonymize(self, text: str) -> str: ...
