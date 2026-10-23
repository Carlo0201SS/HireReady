from functools import lru_cache

from backend.application.anonymization_service import AnonymizationService
from backend.application.cv_extraction_service import CVExtractionService
from backend.application.cv_parser_orchestrator import CVParserOrchestrator

from backend.domain.models.cv import CVInterviewContext


from backend.manager.cv.docx_extractor import DocxExtractor
from backend.manager.cv.pymupdf_extractor import PyMuPDFExtractor
from backend.manager.cv.rizzo_anonymizer import RizzoAnonymizer
from backend.manager.llm.gemma_cv_parser import GemmaCVParser


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
