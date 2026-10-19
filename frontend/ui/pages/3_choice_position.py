import streamlit as st

from frontend.api_client import BackendApiError, api_client


st.title("Posizione di candidatura")

st.header("Posizione di candidatura", text_alignment="center")

with st.form("position_selection"):
	st.selectbox(
		"Seleziona la posizione per cui vuoi candidarti",
		options=["Sviluppatore web React", "ML Engineer", "AI Agent Enthusiast", "Sviluppatore Android Kotlin"],
	)
	st.form_submit_button("Conferma posizione")

