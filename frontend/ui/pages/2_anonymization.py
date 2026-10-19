from pathlib import Path

import streamlit as st

from frontend.api_client import BackendApiError, api_client


st.title("Anonimizzazione del CV")

source_text = st.session_state.get("extracted_cv_text", "")
if not source_text:
	st.info("Carica prima un CV nella pagina dedicata.")
	st.page_link(
		str(Path(__file__).resolve().with_name("1_upload_cv.py")),
		label="Vai al caricamento del CV",
	)
	st.stop()

try:
	model_available = api_client.anonymization_available()
except BackendApiError as error:
	st.error(str(error))
	st.stop()

if not model_available:
	st.warning("Il modello Rizzo PII non è ancora presente in locale.")
	st.code(
		"pip install -r requirements.txt\n"
		"python -m backend.infrastructure.cv.rizzo_anonymizer",
		language="powershell",
	)

if st.button("Anonimizza CV", type="primary", disabled=not model_available):
	with st.spinner("Analisi e anonimizzazione in corso..."):
		try:
			anonymized_text = api_client.anonymize_cv(source_text)
		except BackendApiError as error:
			st.error(str(error))
		except Exception:
			st.error("Anonimizzazione non riuscita. Verifica il modello locale e riprova.")
		else:
			st.session_state["anonymized_cv_text"] = anonymized_text
			st.session_state["anonymized_source_text"] = source_text
			st.success("Anonimizzazione completata.")

current_anonymized_text = ""
if st.session_state.get("anonymized_source_text") == source_text:
	current_anonymized_text = st.session_state.get("anonymized_cv_text", "")

original_column, anonymized_column = st.columns(2)
with original_column:
	st.text_area("Testo originale", value=source_text, height=360, disabled=True)
with anonymized_column:
	st.text_area("Testo anonimizzato", value=current_anonymized_text, height=360, disabled=True)

if st.button("Cancella CV e risultati dalla sessione"):
	for key in (
		"cv_file_upload",
		"extracted_cv_text",
		"anonymized_cv_text",
		"anonymized_source_text",
	):
		st.session_state.pop(key, None)
	st.rerun()
