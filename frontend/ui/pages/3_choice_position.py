import logging
from pathlib import Path

import streamlit as st

from backend.controller import reset_interview_session, submit_anonymization
from frontend.api_client import BackendApiError, api_client


st.title("Posizione di candidatura")

st.header("Posizione di candidatura", text_alignment="center")

source_cv = st.session_state.get("extracted_cv_text", "")

if not source_cv:
	st.info("Carica prima un CV nella pagina dedicata.")
	st.page_link(
		str(Path(__file__).resolve().with_name("1_upload_cv.py")),
		label="Vai al caricamento del CV",
	)
	st.stop()

selected_position = st.selectbox(
	"Seleziona la posizione per cui vuoi candidarti",
	options=["Sviluppatore web React", "ML Engineer", "AI Agent Enthusiast", "Sviluppatore Android Kotlin"],
)
position_description = st.text_area(
	"Descrizione o dettagli della posizione (facoltativo)",
	placeholder="Aggiungi responsabilità, requisiti o argomenti che vuoi approfondire nel colloquio.",
	help="Queste informazioni verranno usate per adattare l'analisi del CV e le domande del colloquio.",
)
submitted = st.button("Conferma posizione", type="primary")

if submitted:
	st.session_state["selected_position"] = selected_position
	anonymized_cv = st.session_state.get("anonymized_cv_text", "")
	if st.session_state.get("anonymized_source_text") != source_cv:
		anonymized_cv = ""

	future = st.session_state.get("cv_anonymization_future")
	if (
		not anonymized_cv
		and (
			future is None
			or st.session_state.get("cv_anonymization_source_text") != source_cv
		)
	):
		future = submit_anonymization(
			source_cv,
			api_client.anonymize_cv,
			api_client.anonymization_status,
		)
		st.session_state["cv_anonymization_future"] = future
		st.session_state["cv_anonymization_source_text"] = source_cv

	with st.spinner("Preparazione del CV e analisi della posizione selezionata..."):
		try:
			if not anonymized_cv:
				try:
					anonymized_cv = future.result()
				except BackendApiError as error:
					st.session_state.pop("cv_anonymization_future", None)
					st.session_state.pop("cv_anonymization_source_text", None)
					st.error(str(error))
					st.stop()
				except Exception as error:
					st.session_state.pop("cv_anonymization_future", None)
					st.session_state.pop("cv_anonymization_source_text", None)
					logging.exception("Errore durante l'anonimizzazione automatica del CV")
					st.error(
						"Preparazione del CV non riuscita. "
						"Conferma di nuovo la posizione per riprovare."
					)
					st.stop()

				st.session_state["anonymized_cv_text"] = anonymized_cv
				st.session_state["anonymized_source_text"] = source_cv

			parsed_context = api_client.parse_cv_for_interview(
				anonymized_cv=anonymized_cv,
				selected_position=selected_position,
				position_description=position_description,
			)
		except BackendApiError as error:
			st.error(str(error))
		else:
			reset_interview_session(st.session_state)
			st.session_state["cv_interview_context"] = parsed_context
			st.success("Profilo estratto e salvato nella sessione.")
			st.json(parsed_context["profile"])
			st.switch_page(str(Path(__file__).resolve().with_name("4_interview.py")))
