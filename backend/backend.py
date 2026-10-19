from functools import lru_cache

from backend.application.anonymization_service import AnonymizationService
from backend.application.cv_extraction_service import CVExtractionService
from backend.infrastructure.cv.docx_extractor import DocxExtractor
from backend.infrastructure.cv.pymupdf_extractor import PyMuPDFExtractor
from backend.infrastructure.cv.rizzo_anonymizer import RizzoAnonymizer


@lru_cache(maxsize=1) # lru_cache memorizza il risultato della funzione.
def _anonymization_service() -> AnonymizationService:
	return AnonymizationService(RizzoAnonymizer())


@lru_cache(maxsize=1) # //
def _cv_extraction_service() -> CVExtractionService:
	return CVExtractionService(PyMuPDFExtractor(), DocxExtractor())


def is_anonymization_available() -> bool:
	return _anonymization_service().is_available


def anonymize_cv(text: str) -> str:
	return _anonymization_service().anonymize(text)


def extract_cv_text(filename: str, content: bytes) -> str:
	return _cv_extraction_service().extract_text(filename, content)
