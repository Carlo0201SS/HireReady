from io import BytesIO
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


class DocxExtractor:
	def extract_text(self, docx_path: str | Path) -> str:
		path = Path(docx_path)
		if path.suffix.lower() != ".docx":
			raise ValueError("Il file da estrarre deve essere un DOCX.")

		return self._extract_document(Document(path))

	def extract_text_from_bytes(self, docx_bytes: bytes) -> str:
		return self._extract_document(Document(BytesIO(docx_bytes)))

	@staticmethod
	def _extract_document(document) -> str:
		blocks = []
		for item in document.iter_inner_content():
			if isinstance(item, Paragraph):
				text = item.text.strip()
				if text:
					blocks.append(text)
			elif isinstance(item, Table):
				rows = [
					" | ".join(cell.text.strip() for cell in row.cells).strip(" |")
					for row in item.rows
				]
				blocks.extend(row for row in rows if row)

		return "\n\n".join(blocks)
