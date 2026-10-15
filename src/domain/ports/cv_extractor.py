from typing import Protocol


class CVExtractor(Protocol):
	def extract_text_from_bytes(self, content: bytes) -> str: ...
