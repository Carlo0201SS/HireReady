from backend.domain.ports.anonymizer import Anonymizer

# E' un livello di astrazione, il quale non dipende da alcuna libreria o precisa implementazione.
class AnonymizationService:
	def __init__(self, anonymizer: Anonymizer) -> None:
		self._anonymizer = anonymizer

	@property
	def is_available(self) -> bool:
		return self._anonymizer.is_available

	def anonymize(self, text: str) -> str:
		return self._anonymizer.anonymize(text)
