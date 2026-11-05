import logging
from hashlib import sha256
from pathlib import Path

import streamlit as st

from frontend.services.cv_anonymization import submit_anonymization
from frontend.services.interview_session import reset_interview_session
from frontend.api_client import BackendApiError, api_client


st.title("Carica il CV") 

uploaded_file = st.file_uploader(
	"Seleziona un CV in formato PDF o DOCX",
	type=["pdf", "docx"],
	key="cv_file_upload",
)
extracted_text = st.session_state.get("extracted_cv_text", "")

if uploaded_file is not None:
	file_bytes = uploaded_file.getvalue()
	upload_signature = sha256(uploaded_file.name.encode() + b"\0" + file_bytes).hexdigest()
	if upload_signature != st.session_state.get("extracted_cv_upload_signature"):
		old_future = st.session_state.get("cv_anonymization_future")
		if old_future is not None:
			old_future.cancel()
		for key in (
			"extracted_cv_text",
			"anonymized_cv_text",
			"anonymized_source_text",
			"cv_anonymization_future",
			"cv_anonymization_source_text",
			"extracted_cv_upload_signature",
			"selected_position",
			"cv_interview_context",
		):
			st.session_state.pop(key, None)
		reset_interview_session(st.session_state)
		extracted_text = ""

	if not extracted_text:
		try:
			extracted_text = api_client.extract_cv_text(uploaded_file.name, file_bytes)
		except BackendApiError as error:
			st.session_state["extracted_cv_text"] = ""
			st.error(str(error))
		except Exception as error:
			logging.exception("Errore inatteso durante l'estrazione del CV")
			st.session_state["extracted_cv_text"] = ""
			st.error(f"Errore inatteso nel frontend ({type(error).__name__}). Dettagli qui sotto.")
			with st.expander("Dettagli tecnici"):
				st.exception(error)
		else:
			st.session_state["extracted_cv_text"] = extracted_text
			st.session_state["extracted_cv_upload_signature"] = upload_signature
			if extracted_text:
				st.success("Estrazione completata.")
			else:
				if Path(uploaded_file.name).suffix.lower() == ".pdf":
					st.warning("Nessun testo selezionabile trovato. I PDF scansionati richiedono OCR.")
				else:
					st.warning("Nessun testo estraibile trovato nel documento.")

if extracted_text:
	future = st.session_state.get("cv_anonymization_future")
	if (
		future is None
		or st.session_state.get("cv_anonymization_source_text") != extracted_text
	):
		st.session_state["cv_anonymization_future"] = submit_anonymization(
			extracted_text,
			api_client.anonymize_cv,
			api_client.anonymization_status,
		)
		st.session_state["cv_anonymization_source_text"] = extracted_text

st.text_area("Testo estratto", value=extracted_text, height=360, disabled=True)

if extracted_text:
	spacer, proceed_column = st.columns([4, 1])
	with proceed_column:
		if st.button("Scegli la posizione", type="primary", use_container_width=True):
			st.switch_page(str(Path(__file__).resolve().with_name("3_choice_position.py")))
