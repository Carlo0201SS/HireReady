from typing import Protocol, Any, Callable, Mapping


# firma del metodo, la logica si trova in manager/
class TextToSpeech(Protocol):
    @property
    def is_available(self) -> bool: ...

    @property
    def state(self) -> str: ...

    def warm_up(self) -> None: ...

    def synthesize(self, text: str) -> bytes: ...

    def submit_synthesis(self, source_text: str,
        synthesize: Callable[[str], bytes],
        get_status: Callable[[], Mapping[str, Any]]) -> str: ...