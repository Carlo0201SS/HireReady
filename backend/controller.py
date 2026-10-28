from functools import lru_cache

from backend.application.anonymization_service import AnonymizationService
from backend.application.cv_extraction_service import CVExtractionService
from backend.application.cv_parser_orchestrator import CVParserOrchestrator

from backend.domain.models.cv_model import CVInterviewContext
from backend.domain.models.interview_model import HireReadyTurn



from backend.manager.cv.docx_extractor import DocxExtractor
from backend.manager.cv.pymupdf_extractor import PyMuPDFExtractor
from backend.manager.cv.rizzo_anonymizer import RizzoAnonymizer
from backend.manager.llm.gemma_cv_parser import GemmaCVParser
from backend.manager.llm.gemma_interview import GemmaInterview, InterviewState


@lru_cache(maxsize=1) # lru_cache memorizza il risultato della funzione.
def _anonymization_service() -> AnonymizationService:
	return AnonymizationService(RizzoAnonymizer())


@lru_cache(maxsize=1) # //
def _cv_extraction_service() -> CVExtractionService:
	return CVExtractionService(PyMuPDFExtractor(), DocxExtractor())


def warm_up_anonymization() -> None:
	_anonymization_service().warm_up()


def anonymization_state() -> str:
	return _anonymization_service().state


def is_anonymization_available() -> bool:
	return _anonymization_service().is_available


def anonymize_cv(text: str) -> str:
	return _anonymization_service().anonymize(text)


def extract_cv_text(filename: str, content: bytes) -> str:
	return _cv_extraction_service().extract_text(filename, content)


def parse_cv_for_interview(
	*,
	anonymized_cv: str,
	selected_position: str,
) -> CVInterviewContext:
	orchestrator = CVParserOrchestrator(GemmaCVParser())
	return orchestrator.parse_for_interview(
		anonymized_cv=anonymized_cv,
		selected_position=selected_position,
	)

@lru_cache(maxsize=1)
def _interview_service() -> GemmaInterview:
	return GemmaInterview()


def _rebuild_state(history: list[dict[str, str]], last_turn: HireReadyTurn) -> InterviewState:
	# Il backend è stateless: lo stato del colloquio arriva dal client a ogni turno.
	return InterviewState(
		turn_id=last_turn.turn_id,
		history=list(history),
		is_closed=last_turn.is_final,
		last_turn=last_turn,
	)


def interview_handle(
	*,
	history: list[dict[str, str]],
	last_turn: HireReadyTurn | None,
	candidate_answer: str | None,
	selected_position: str | None,
	profile,
) -> tuple[HireReadyTurn, InterviewState]:
	service = _interview_service()

	if last_turn is None:
		# Turno 0: bootstrap
		if not selected_position or profile is None:
			raise ValueError("Al primo turno servono 'selected_position' e 'profile'.")
		return service.start(position=selected_position, candidate_profile=profile)

	# Turni successivi: ricostruisce lo stato dal payload (stateless)
	if not candidate_answer or not candidate_answer.strip():
		raise ValueError("Nei turni successivi 'candidate_answer' è obbligatoria.")

	state = _rebuild_state(history, last_turn)
	turn = service.next_turn(state=state, candidate_answer=candidate_answer)
	return turn, state

def interview_service_start(*, position, candidate_profile):
	return _interview_service().start(
		position=position,
		candidate_profile=candidate_profile,
	)


def interview_service_turn(*, history, last_turn, candidate_answer):
	# Ricostruisce InterviewState da quanto arriva dal client (stateless)
	state = _rebuild_state(history, last_turn)
	turn = _interview_service().next_turn(
		state=state,
		candidate_answer=candidate_answer,
	)
	return turn, state
