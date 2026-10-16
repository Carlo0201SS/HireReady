import streamlit as st

from backend.backend import anonymize_cv, is_anonymization_available


st.title("Anonimizzazione del CV")

source_text = st.session_state.get("extracted_cv_text", "")
if not source_text:
	st.info("Carica prima un CV nella pagina dedicata.")
	st.page_link("frontend/ui/pages/1_upload_cv.py", label="Vai al caricamento del CV")
	st.stop()

model_available = is_anonymization_available()
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
			anonymized_text = anonymize_cv(source_text)
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
