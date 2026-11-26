import logging
from hashlib import sha256
from pathlib import Path

import streamlit as st
from fastapi import HTTPException

from backend.controller import reset_interview_session, submit_anonymization
from frontend.api_client import api_client


# ----------------------------------------------------------------------
# CARICAMENTO DEL CV (testata e percorso sono in app.py)
# ----------------------------------------------------------------------
st.markdown(
	"""
	<style>
	.carica-titolo { font-size: 20px; font-weight: 700; color: #1f3a5f; margin-bottom: 2px; }
	.carica-nota { font-size: 14px; color: #5b6b7d; margin-bottom: 12px; }
	</style>
	""",
	unsafe_allow_html=True,
)

carica_cv = st.container(key="riquadro_cv")
with carica_cv:
	st.markdown('<div class="progress-fase">Passo 1 di 5</div>', unsafe_allow_html=True)
	st.markdown('<div class="carica-titolo">Carica il tuo CV</div>', unsafe_allow_html=True)
	st.markdown(
		'<div class="carica-nota">🔒 Il CV viene anonimizzato e tutto gira in locale: '
		"nessun dato esce dal tuo computer.</div>",
		unsafe_allow_html=True,
	)
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
			except HTTPException as error:
				st.session_state["extracted_cv_text"] = ""
				if error.status_code == 503:
					# Backend non raggiungibile: messaggio chiaro, dettaglio tecnico a parte
					st.error("Il servizio di analisi non risponde. Verifica che il backend sia avviato e riprova.")
					with st.expander("Dettagli tecnici"):
						st.code(str(error.detail))
				else:
					st.error(str(error.detail))
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

	if extracted_text:
		# Il testo estratto serve come verifica: lo mostriamo solo se richiesto
		with st.expander(f"Testo estratto ({len(extracted_text.split())} parole)"):
			st.text_area("Testo estratto", value=extracted_text, height=360, disabled=True, label_visibility="collapsed")

		if st.button("Scegli la posizione ➜", type="primary", use_container_width=True):
			st.switch_page(str(Path(__file__).resolve().with_name("3_choice_position.py")))
