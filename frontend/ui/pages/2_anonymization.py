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
	model_status = api_client.anonymization_status()
except BackendApiError as error:
	st.error(str(error))
	st.stop()

model_state = model_status.get("state", "idle")
model_available = model_status["available"] and model_state != "error"
pending_messages = {
	"downloading": "Il backend sta scaricando il modello Rizzo PII (circa 1,2 GB): serve solo la prima volta.",
	"loading": "Il backend sta caricando in memoria il modello Rizzo PII.",
}
if model_state == "error":
	st.error(
		"Preparazione del modello Rizzo PII non riuscita. "
		"Controlla il terminale del backend e riavvialo."
	)
elif model_state in pending_messages or not model_available:
	st.info(pending_messages.get(model_state, "Il modello Rizzo PII non è ancora pronto."))
	if st.button("Aggiorna stato"):
		st.rerun()

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

if current_anonymized_text and st.button("Scegli la posizione", type="primary"):
	st.switch_page(str(Path(__file__).resolve().with_name("3_choice_position.py")))

if st.button("Cancella CV e risultati dalla sessione"):
	for key in (
		"cv_file_upload",
		"extracted_cv_text",
		"anonymized_cv_text",
		"anonymized_source_text",
	):
		st.session_state.pop(key, None)
	st.rerun()
