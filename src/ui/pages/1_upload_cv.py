from pathlib import Path

import streamlit as st

from src.backend import extract_cv_text


st.title("Carica il CV") 

uploaded_file = st.file_uploader(
	"Seleziona un CV in formato PDF o DOCX",
	type=["pdf", "docx"],
	key="cv_file_upload",
)
extracted_text = st.session_state.get("extracted_cv_text", "")

if uploaded_file is not None:
	try:
		file_bytes = uploaded_file.getvalue()
		extracted_text = extract_cv_text(uploaded_file.name, file_bytes)
	except Exception:
		extracted_text = ""
		st.session_state["extracted_cv_text"] = ""
		st.error("Impossibile leggere il documento. Verifica che sia valido e non protetto da password.")
	else:
		st.session_state["extracted_cv_text"] = extracted_text
		if extracted_text:
			st.success("Estrazione completata.")
		else:
			if Path(uploaded_file.name).suffix.lower() == ".pdf":
				st.warning("Nessun testo selezionabile trovato. I PDF scansionati richiedono OCR.")
			else:
				st.warning("Nessun testo estraibile trovato nel documento.")

st.text_area("Testo estratto", value=extracted_text, height=360, disabled=True)

if extracted_text:
	spacer, proceed_column = st.columns([4, 1])
	with proceed_column:
		if st.button("Procedi all'anonimizzazione", type="primary", use_container_width=True):
			st.switch_page("src/ui/pages/2_anonymization.py")
