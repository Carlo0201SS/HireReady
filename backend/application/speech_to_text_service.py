from backend.domain.ports.speech import TextToSpeech


# E' un livello di astrazione, il quale non dipende da alcuna libreria o precisa implementazione.
class SpeechToTextService:
	def __init__(self, text_to_speech: TextToSpeech) -> None:
		self._text_to_speech = text_to_speech

	@property
	def is_available(self) -> bool:
		return self._text_to_speech.is_available

	@property
	def state(self) -> str:
		return self._text_to_speech.state

	def warm_up(self) -> None:
		self._text_to_speech.warm_up()

	def synthesize(self, text: str) -> bytes:
		return self._text_to_speech.synthesize(text)

	def submit_synthesis(
		self,
		source_text: str,
		synthesize,
		get_status,
	) -> str:
		return self._text_to_speech.submit_synthesis(
			source_text,
			synthesize,
			get_status,
		)