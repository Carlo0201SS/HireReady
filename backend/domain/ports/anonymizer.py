from typing import Protocol, Any, Callable, Mapping

# firma del metodo, la logica si trova in infrastructure/
class Anonymizer(Protocol):
	@property
	def is_available(self) -> bool: ...

	@property
	def state(self) -> str: ...

	def warm_up(self) -> None: ...

	def anonymize(self, text: str) -> str: ...

	def submit_anonymization(self, source_text: str,
		anonymize: Callable[[str], str],
		get_status: Callable[[], Mapping[str, Any]]) -> str: ...
