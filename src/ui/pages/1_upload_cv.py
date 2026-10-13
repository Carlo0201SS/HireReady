from pathlib import Path

import streamlit as st

from src.infrastructure.cv.docx_extractor import DocxExtractor
from src.infrastructure.cv.pymupdf_extractor import PyMuPDFExtractor


st.title("Carica il CV")

uploaded_file = st.file_uploader("Seleziona un CV in formato PDF o DOCX", type=["pdf", "docx"])
extracted_text = ""

if uploaded_file is not None:
	try:
		file_bytes = uploaded_file.getvalue()
		if Path(uploaded_file.name).suffix.lower() == ".docx":
			extracted_text = DocxExtractor().extract_text_from_bytes(file_bytes)
		else:
			extracted_text = PyMuPDFExtractor().extract_text_from_bytes(file_bytes)
	except Exception:
		st.error("Impossibile leggere il documento. Verifica che sia valido e non protetto da password.")
	else:
		if extracted_text:
			st.success("Estrazione completata.")
		else:
			if Path(uploaded_file.name).suffix.lower() == ".pdf":
				st.warning("Nessun testo selezionabile trovato. I PDF scansionati richiedono OCR.")
			else:
				st.warning("Nessun testo estraibile trovato nel documento.")

st.text_area("Testo estratto", value=extracted_text, height=360, disabled=True)
