from typing import Protocol

# firma del metodo, la logica si trova in infrastructure/
class Anonymizer(Protocol):
	@property
	def is_available(self) -> bool: ...

	def anonymize(self, text: str) -> str: ...
