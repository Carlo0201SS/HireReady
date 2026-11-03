from concurrent.futures import Future, ThreadPoolExecutor
from time import monotonic, sleep
from typing import Any, Callable, Mapping


_ANONYMIZATION_EXECUTOR = ThreadPoolExecutor(
	max_workers=1,
	thread_name_prefix="cv-anonymization",
)
_ANONYMIZATION_TIMEOUT_SECONDS = 900
_ANONYMIZATION_POLL_INTERVAL_SECONDS = 1


def _anonymize_when_ready(
	source_text: str,
	anonymize: Callable[[str], str],
	get_status: Callable[[], Mapping[str, Any]],
) -> str:
	deadline = monotonic() + _ANONYMIZATION_TIMEOUT_SECONDS
	while True:
		status = get_status()
		state = status.get("state", "idle")
		if state == "error":
			raise RuntimeError("La preparazione del modello di anonimizzazione è fallita.")
		if status.get("available") and state not in {"downloading", "loading"}:
			return anonymize(source_text)
		if monotonic() >= deadline:
			raise TimeoutError(
				"Il modello di anonimizzazione non è diventato disponibile entro 15 minuti."
			)
		sleep(_ANONYMIZATION_POLL_INTERVAL_SECONDS)


def submit_anonymization(
	source_text: str,
	anonymize: Callable[[str], str],
	get_status: Callable[[], Mapping[str, Any]],
) -> Future[str]:
	if not source_text.strip():
		raise ValueError("Il testo del CV da anonimizzare è vuoto.")
	return _ANONYMIZATION_EXECUTOR.submit(
		_anonymize_when_ready,
		source_text,
		anonymize,
		get_status,
	)
