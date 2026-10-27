from pathlib import Path
import streamlit as st

from interops.api_client import BackendApiError, api_client


st.title("Posizione di candidatura")

st.header("Posizione di candidatura", text_alignment="center")

anonymized_cv = st.session_state.get("anonymized_cv_text", "")
anonymized_source = st.session_state.get("anonymized_source_text", "")
source_cv = st.session_state.get("extracted_cv_text", "")

if not anonymized_cv or anonymized_source != source_cv:
	st.info("Anonimizza il CV aggiornato prima di scegliere la posizione.")
	st.page_link(
		str(Path(__file__).resolve().with_name("2_anonymization.py")),
		label="Vai all'anonimizzazione",
	)
	st.stop()

with st.form("position_selection"):
	selected_position = st.selectbox(
		"Seleziona la posizione per cui vuoi candidarti",
		options=["Sviluppatore web React", "ML Engineer", "AI Agent Enthusiast", "Sviluppatore Android Kotlin"],
	)
	submitted = st.form_submit_button("Conferma posizione")

if submitted:
	st.session_state["selected_position"] = selected_position
	st.switch_page(str(Path(__file__).resolve().with_name("4_interview.py")))
	with st.spinner("Gemma sta elaborando il CV per la posizione selezionata..."):
		try:
			parsed_context = api_client.parse_cv_for_interview(
				anonymized_cv=anonymized_cv,
				selected_position=selected_position,
			)
		except BackendApiError as error:
			st.error(str(error))
		else:
			st.session_state["cv_interview_context"] = parsed_context
			st.success("Profilo estratto e salvato nella sessione.")
			st.json(parsed_context["profile"])

