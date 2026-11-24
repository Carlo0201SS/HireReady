from collections.abc import MutableMapping
from concurrent.futures import Future, ThreadPoolExecutor
from functools import lru_cache
import os
import time
from typing import Any, Callable, Mapping

from backend.application.anonymization_service import AnonymizationService
from backend.application.cv_extraction_service import CVExtractionService
from backend.application.cv_parser_orchestrator import CVParserOrchestrator

from backend.domain.models.cv_model import CVInterviewContext
from backend.domain.models.interview_model import HireReadyTurn
from backend.domain.models.report_model import (
	InterviewReportRequest,
	InterviewReportResponse,
)

from backend.manager.cv.docx_extractor import DocxExtractor
from backend.manager.cv.pymupdf_extractor import PyMuPDFExtractor
from backend.manager.cv.rizzo_anonymizer import RizzoAnonymizer

from backend.manager.llm.gemma_cv_parser import GemmaCVParser
from backend.manager.llm.gemma_interview import GemmaInterview, InterviewState
from backend.manager.llm.gemma_report import GemmaInterviewReporter
from backend.manager.report.reportlab_pdf_renderer import ReportLabPdfRenderer

from backend.manager.speech.speech_to_text import STTManager


_ANONYMIZATION_EXECUTOR = ThreadPoolExecutor(
	max_workers=1,
	thread_name_prefix="cv-anonymization",
)
_STT_EXECUTOR = ThreadPoolExecutor(
	max_workers=1,
	thread_name_prefix="stt-transcription",
)
_INTERVIEW_SESSION_KEYS = (
	"interview_turn",
	"interview_history",
	"interview_closed",
	"interview_report_answers",
	"interview_report",
	"answer_counter",
)
_REPORT_DIRECTORY = os.path.join(
	os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
	"report",
)


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
	position_description: str = "",
) -> CVInterviewContext:
	orchestrator = CVParserOrchestrator(GemmaCVParser())
	return orchestrator.parse_for_interview(
		anonymized_cv=anonymized_cv,
		selected_position=selected_position,
		position_description=position_description,
	)

#-------CONTROLLER SERVIZIO GEMMA INTERVIEW ---------------------------------

@lru_cache(maxsize=1)
def _interview_service() -> GemmaInterview:
	return GemmaInterview()


#----------- GESTIONE STATO---------------------------------------------------

def submit_anonymization(
	source_text: str,
	anonymize: Callable[[str], str],
	get_status: Callable[[], Mapping[str, Any]],
) -> Future[str]:
	if not source_text.strip():
		raise ValueError("Il testo del CV da anonimizzare è vuoto.")
	return _ANONYMIZATION_EXECUTOR.submit(
		RizzoAnonymizer._anonymize_when_ready,
		source_text,
		anonymize,
		get_status,
	)


def submit_transcription(
	audio_bytes: bytes,
	transcribe: Callable[[bytes], str],
	get_status: Callable[[], Mapping[str, Any]],
) -> Future[str]:
	if not audio_bytes:
		raise ValueError("L'audio da trascrivere è vuoto.")
	return _STT_EXECUTOR.submit(
		_transcribe_when_ready,
		audio_bytes,
		transcribe,
		get_status,
	)


def _transcribe_when_ready(
	audio_bytes: bytes,
	transcribe: Callable[[bytes], str],
	get_status: Callable[[], Mapping[str, Any]],
) -> str:
	# Attende che il modello STT sia pronto (stesso pattern di RizzoAnonymizer)
	while get_status().get("state") != "ready":
		time.sleep(0.5)
	return transcribe(audio_bytes)


def reset_interview_session(session_state: MutableMapping[str, Any]) -> None:
	for key in _INTERVIEW_SESSION_KEYS:
		session_state.pop(key, None)

#----------GESTIONE INTERVIEW ---------------------------------------------------------
def interview_handle(
	*,
	history: list[dict[str, str]],
	anonymized_cv: str,
	last_turn: HireReadyTurn | None,
	candidate_answer: str | None,
	selected_position: str | None,
	level_position: str | None,
	profile,
	position_description: str | None = None,
) -> tuple[HireReadyTurn, InterviewState]:
	service = _interview_service()

	if last_turn is None:
		# Turno 0: bootstrap
		if not selected_position or not level_position or profile is None:
			raise ValueError(
				"Al primo turno servono 'selected_position', 'level_position' e 'profile'."
			)
		return service.start(
			position=selected_position,
			level_position=level_position,
			candidate_profile=profile,
			position_description=position_description or "",
			anonymized_cv=anonymized_cv,
		)

	# Turni successivi: ricostruisce lo stato dal payload (stateless)
	if not candidate_answer or not candidate_answer.strip():
		raise ValueError("Nei turni successivi 'candidate_answer' è obbligatoria.")

	state = _interview_service()._rebuild_state(history, last_turn, anonymized_cv)
	turn = service.next_turn(state=state, candidate_answer=candidate_answer)
	return turn, state

def interview_service_start(
	*,
	position,
	level_position,
	candidate_profile,
	anonymized_cv,
	position_description="",
):
	return _interview_service().start(
		position=position,
		level_position=level_position,
		candidate_profile=candidate_profile,
		position_description=position_description,
		anonymized_cv=anonymized_cv,
	)


def interview_service_turn(*, history, last_turn, candidate_answer, anonymized_cv):
	# Ricostruisce InterviewState da quanto arriva dal client (stateless)
	state = _interview_service()._rebuild_state(history, last_turn, anonymized_cv)
	turn = _interview_service().next_turn(
		state=state,
		candidate_answer=candidate_answer,
	)
	return turn, state

# ------ SERVIZIO REPORT ---------------------------------------

@lru_cache(maxsize=1)
def _interview_reporter() -> GemmaInterviewReporter:
	return GemmaInterviewReporter()

#---- GESTIONE REPORT -----------------------------------------

def generate_interview_report(
	request: InterviewReportRequest,
) -> InterviewReportResponse:
	summary = _interview_reporter().summarize(
		request.history,
		request.contenuto,
	)
	return InterviewReportResponse(
		summary=summary.summary,
		intervention_points=summary.intervention_points,
		contenuto=request.contenuto,
		answers=request.answers,
		score=request.score,
	)


@lru_cache(maxsize=1)
def _report_pdf_renderer() -> ReportLabPdfRenderer:
	return ReportLabPdfRenderer()


def generate_report_pdf(report: InterviewReportResponse) -> bytes:
	return _report_pdf_renderer().render(report)


def save_report_pdf(pdf: bytes) -> str:
	os.makedirs(_REPORT_DIRECTORY, exist_ok=True)
	filename_prefix = "report_colloquio_"
	existing_indices = []
	for existing_filename in os.listdir(_REPORT_DIRECTORY):
		if existing_filename.startswith(filename_prefix) and existing_filename.endswith(
			".pdf"
		):
			index_text = existing_filename[len(filename_prefix) : -len(".pdf")]
			if index_text.isdigit():
				existing_indices.append(int(index_text))
	index = max(existing_indices, default=0) + 1
	while True:
		filename = f"{filename_prefix}{index}.pdf"
		file_path = os.path.join(_REPORT_DIRECTORY, filename)
		try:
			with open(file_path, "xb") as report_file:
				report_file.write(pdf)
			return filename
		except FileExistsError:
			index += 1

# ------ SERVIZIO SPEECH-TO-TEXT ---------------------------------------

@lru_cache(maxsize=1)
def _stt_manager() -> STTManager:
	return STTManager(
		model_size=os.getenv("HIREREADY_STT_MODEL_SIZE", "small"),
		device=os.getenv("HIREREADY_STT_DEVICE", "cpu"),
		compute_type=os.getenv("HIREREADY_STT_COMPUTE_TYPE", "int8"),
	)


def warm_up_stt() -> None:
	_stt_manager().warm_up()


def stt_state() -> str:
	return _stt_manager().state


def is_stt_available() -> bool:
	return _stt_manager().is_ready


def transcribe_audio(
	audio_bytes: bytes,
	language: str | None = None,
	beam_size: int = 5,
	vad_filter: bool = True,
) -> dict:
	return _stt_manager().transcribe(
		audio_bytes,
		language=language,
		beam_size=beam_size,
		vad_filter=vad_filter,
	)


def transcribe_audio_to_text(
	audio_bytes: bytes,
	language: str | None = None,
) -> str:
	return _stt_manager().transcribe_to_text(audio_bytes, language=language)