import logging
from pathlib import Path

import streamlit as st

from interops.api_client import BackendApiError, api_client


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
		extracted_text = api_client.extract_cv_text(uploaded_file.name, file_bytes)
	except BackendApiError as error:
		extracted_text = ""
		st.session_state["extracted_cv_text"] = ""
		st.error(str(error))
	except Exception as error:
		logging.exception("Errore inatteso durante l'estrazione del CV")
		extracted_text = ""
		st.session_state["extracted_cv_text"] = ""
		st.error(f"Errore inatteso nel frontend ({type(error).__name__}). Dettagli qui sotto.")
		with st.expander("Dettagli tecnici"):
			st.exception(error)
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
			st.switch_page(str(Path(__file__).resolve().with_name("2_anonymization.py")))
