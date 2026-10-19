from typing import Protocol

# firma del metodo, la logica si trova in infrastructure/
class CVExtractor(Protocol):
	# i bytes vengono passati al servizio che li estrae ( che si trova in infrastructure)
	#non è obbligatorio farlo, ma in contesto web si fa.
	def extract_text_from_bytes(self, content: bytes) -> str: ...
