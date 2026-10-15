from pathlib import Path

from src.domain.ports.cv_extractor import CVExtractor


class CVExtractionService:
	def __init__(self, pdf_extractor: CVExtractor, docx_extractor: CVExtractor) -> None:
		self._extractors = {
			".pdf": pdf_extractor,
			".docx": docx_extractor,
		}

	def extract_text(self, filename: str, content: bytes) -> str:
		suffix = Path(filename).suffix.lower()
		try:
			extractor = self._extractors[suffix]
		except KeyError as error:
			raise ValueError("Il CV deve essere in formato PDF o DOCX.") from error

		return extractor.extract_text_from_bytes(content)