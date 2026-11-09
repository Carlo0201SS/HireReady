from pathlib import Path

import streamlit as st


st.set_page_config(
	page_title="HireReady | Livello",
	page_icon="🎯",
	layout="wide",
)

context = st.session_state.get("cv_interview_context")
if not context:
	st.info("Prima di scegliere il livello devi confermare la posizione.")
	st.page_link(
		str(Path(__file__).resolve().with_name("3_choice_position.py")),
		label="Vai alla scelta della posizione",
	)
	st.stop()

st.title("Livello di esperienza")
st.write(
	"Seleziona il livello che descrive meglio la tua esperienza. "
	"Il livello verrà usato per calibrare la difficoltà delle domande."
)

levels = ["junior", "middle", "senior"]
current_level = st.session_state.get("level_position", "middle")
default_index = levels.index(current_level) if current_level in levels else 1

level_position = st.selectbox(
	"Seleziona il tuo livello",
	options=levels,
	format_func=str.title,
	index=default_index,
)

if st.button("Conferma livello e continua ➜", type="primary"):
	st.session_state["level_position"] = level_position
	st.switch_page(str(Path(__file__).resolve().with_name("4_interview.py")))
