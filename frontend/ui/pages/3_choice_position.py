import logging
from pathlib import Path

import streamlit as st
from fastapi import HTTPException

from backend.controller import reset_interview_session, submit_anonymization
from frontend.api_client import api_client


st.markdown('<div class="progress-fase">Passo 2 di 5</div>', unsafe_allow_html=True)
st.markdown('<div class="titolo-pagina">Posizione di candidatura</div>', unsafe_allow_html=True)
st.markdown(
	'<div class="sottotitolo-pagina">Scegli il ruolo e, se vuoi, incolla l\'annuncio: '
	"le domande del colloquio saranno costruite su quella posizione.</div>",
	unsafe_allow_html=True,
)

st.session_state.setdefault("position_processing", False)

source_cv = st.session_state.get("extracted_cv_text", "")

if not source_cv:
	st.session_state["position_processing"] = False
	st.info("Carica prima un CV nella pagina dedicata.")
	st.page_link(
		str(Path(__file__).resolve().with_name("1_upload_cv.py")),
		label="Vai al caricamento del CV",
	)
	st.stop()

# Campi della pagina nel riquadro chiaro comune (stile in app.py)
with st.container(key="riquadro_posizione"):
	#--------- SCELTA POSIZIONE -----------------------------------
	st.selectbox(
		"Seleziona la posizione per cui vuoi candidarti",
		options=["Sviluppatore web React", "Sviluppatore backend .NET", "AI Engineer", "Machine learning Engineer", "Sviluppatore Android Kotlin", "Agentic AI Engineer", "Data Scientist"],
		key="position_selection",
		disabled=st.session_state["position_processing"],
	)
	#-------------- DESCRIZIONE DELLA POSIZIONE---------------------
	st.text_area(
		"Descrizione o dettagli della posizione (facoltativo)",
		placeholder="Incolla l'annuncio oppure aggiungi responsabilità, requisiti o argomenti che vuoi approfondire nel colloquio.",
		height=160,
		help="Queste informazioni verranno usate per adattare l'analisi del CV e le domande del colloquio.",
		key="position_description",
		disabled=st.session_state["position_processing"],
	)

	#---PROCESSAMENTO INFORMAZIONI-----------------------------

	def _start_position_processing() -> None:
		st.session_state["selected_position"] = st.session_state["position_selection"]
		st.session_state["submitted_position_description"] = st.session_state[
			"position_description"
		]
		st.session_state["position_processing"] = True


	if not st.session_state["position_processing"]:
		st.button(
			"Conferma posizione ➜",
			type="primary",
			on_click=_start_position_processing,
			disabled=st.session_state["position_processing"],
		)

	processing_error = st.session_state.pop("position_processing_error", None)
	if processing_error:
		st.error(processing_error)

	if st.session_state["position_processing"]:
		anonymized_cv = st.session_state.get("anonymized_cv_text", "")
		if st.session_state.get("anonymized_source_text") != source_cv:
			anonymized_cv = ""

		with st.spinner("Anonimizzazione del CV e analisi della posizione… può richiedere qualche minuto."):
			awaiting_anonymization = not anonymized_cv
			try:
				if awaiting_anonymization:
					future = st.session_state.get("cv_anonymization_future")
					if (
						future is None
						or st.session_state.get("cv_anonymization_source_text") != source_cv
					):
						future = submit_anonymization(
							source_cv,
							api_client.anonymize_cv,
							api_client.anonymization_status,
						)
						st.session_state["cv_anonymization_future"] = future
						st.session_state["cv_anonymization_source_text"] = source_cv
					anonymized_cv = future.result()
					st.session_state["anonymized_cv_text"] = anonymized_cv
					st.session_state["anonymized_source_text"] = source_cv

				parsed_context = api_client.parse_cv_for_interview(
					anonymized_cv=anonymized_cv,
					selected_position=st.session_state["selected_position"],
					position_description=st.session_state[
						"submitted_position_description"
					],
				)
			except HTTPException as error:
				st.session_state["position_processing_error"] = str(error.detail)
				if awaiting_anonymization:
					st.session_state.pop("cv_anonymization_future", None)
					st.session_state.pop("cv_anonymization_source_text", None)
				st.session_state["position_processing"] = False
				st.rerun()
			except Exception as error:
				logging.exception("Preparazione del CV o analisi della posizione non riuscita")
				st.session_state["position_processing_error"] = (
					f"{type(error).__name__}: {error}"
				)
				if awaiting_anonymization:
					st.session_state.pop("cv_anonymization_future", None)
					st.session_state.pop("cv_anonymization_source_text", None)
				st.session_state["position_processing"] = False
				st.rerun()
			else:
				reset_interview_session(st.session_state)
				st.session_state.pop("level_position", None)
				st.session_state["cv_interview_context"] = parsed_context
				st.session_state["position_processing"] = False
				st.success("Profilo estratto e salvato nella sessione.")
				st.json(parsed_context["profile"])
				st.switch_page(str(Path(__file__).resolve().with_name("4_level_position.py")))
