from pathlib import Path

import pymupdf


class PyMuPDFExtractor:
	def extract_text(self, pdf_path: str | Path) -> str:
		path = Path(pdf_path)
		if path.suffix.lower() != ".pdf":
			raise ValueError("Il file da estrarre deve essere un PDF.")

		with pymupdf.open(path) as document:
			return self._extract_document(document)

	# al momento del caricamento, il file viene letto in bytes.
	def extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
		with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
			return self._extract_document(document)

	@staticmethod
	def _extract_document(document: pymupdf.Document) -> str:
		pages = [page.get_text("text").strip() for page in document]
		return "\n\n".join(page for page in pages if page)
