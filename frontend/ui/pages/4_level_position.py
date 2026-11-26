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

st.markdown('<div class="progress-fase">Passo 3 di 5</div>', unsafe_allow_html=True)
st.markdown('<div class="titolo-pagina">Livello di esperienza</div>', unsafe_allow_html=True)
st.markdown(
	'<div class="sottotitolo-pagina">Seleziona il livello che descrive meglio la tua esperienza. '
	"Il livello verrà usato per calibrare la difficoltà delle domande.</div>",
	unsafe_allow_html=True,
)

levels = ["junior", "middle", "senior"]
current_level = st.session_state.get("level_position", "middle")
default_index = levels.index(current_level) if current_level in levels else 1

# Scelta nel riquadro chiaro comune (stile in app.py)
with st.container(key="riquadro_livello"):
	level_position = st.radio(
		"Seleziona il tuo livello",
		options=levels,
		format_func=str.title,
		captions=[
			"Fino a 2 anni: basi solide e primi progetti",
			"2-5 anni: autonomia e scelte tecniche motivate",
			"Oltre 5 anni: architettura, trade-off, guida del team",
		],
		index=default_index,
		horizontal=True,
	)
	st.write("")

	if st.button("Conferma livello e continua ➜", type="primary"):
		st.session_state["level_position"] = level_position
		st.switch_page(str(Path(__file__).resolve().with_name("4_interview.py")))
