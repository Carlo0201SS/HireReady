from typing import Protocol

# firma del metodo, la logica si trova in infrastructure/
class CVExtractor(Protocol):
	def extract_text_from_bytes(self, content: bytes) -> str: ...
