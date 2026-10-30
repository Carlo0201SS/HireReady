from pathlib import Path

import streamlit as st

from interops.api_client import BackendApiError, api_client


# ----------------------------------------------------------------------
# CONFIGURAZIONE PAGINA
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Colloquio",
    page_icon="💬",
    layout="wide",
)


# ----------------------------------------------------------------------
# PARAMETRI REGOLABILI
# ----------------------------------------------------------------------
TITOLO_FONT_SIZE = 42


# ----------------------------------------------------------------------
# CSS PERSONALIZZATO
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    .titolo-centrale {{
        text-align: center;
        font-size: {TITOLO_FONT_SIZE}px;
        font-weight: 700;
        color: #1f3a5f;
        margin-top: 10px;
        margin-bottom: 40px;
        font-family: 'Segoe UI', sans-serif;
    }}
    .logo-box {{
        display: flex;
        align-items: center;
        justify-content: center;
        width: 90px;
        height: 90px;
        background: linear-gradient(135deg, #1f3a5f, #4a7fb5);
        color: white;
        font-size: 48px;
        font-weight: bold;
        border-radius: 12px;
        margin-left: 40px;
        margin-top: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        font-family: 'Georgia', serif;
    }}
    .llm-box {{
        background-color: #eef3f9;
        border-left: 5px solid #4a7fb5;
        padding: 18px 22px;
        border-radius: 8px;
        font-size: 16px;
        color: #1f2d3d;
        min-height: 90px;
        margin-top: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        white-space: pre-wrap;
    }}
    .label-rispondi {{
        font-size: 20px;
        font-weight: 600;
        color: #1f3a5f;
        margin-top: 30px;
        margin-bottom: 8px;
    }}
    .fase-badge {{
        display: inline-block;
        padding: 6px 8px;
        border-radius: 12px;
        background: #ffdd57;
        color: #333;
        font-weight: 400;
        margin-top: 6px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# GUARDIA: contesto presente?
# ----------------------------------------------------------------------
context = st.session_state.get("cv_interview_context")
if not context:
    st.info("Prima di iniziare il colloquio devi scegliere una posizione.")
    st.page_link(
        str(Path(__file__).resolve().with_name("3_choice_position.py")),
        label="Vai alla scelta della posizione",
    )
    st.stop()


# ----------------------------------------------------------------------
# BOOTSTRAP COLLOQUIO (turno 0) — una sola volta
# ----------------------------------------------------------------------
if "interview_turn" not in st.session_state:
    try:
        response = api_client.interview(
            selected_position=context["selected_position"],
            profile=context["profile"],
        )
    except BackendApiError as error:
        st.error(str(error))
        st.stop()
    st.session_state["interview_turn"] = response["turn"]
    st.session_state["interview_history"] = response["history"]
    st.session_state["interview_closed"] = response["is_closed"]


current_turn = st.session_state["interview_turn"]
is_closed = st.session_state.get("interview_closed", False)


# ----------------------------------------------------------------------
# TITOLO CENTRALE
# ----------------------------------------------------------------------
titolo = f"Colloquio fase {current_turn.get('phase', '—')}"
st.markdown(f'<div class="titolo-centrale">{titolo}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------
# RIGA: LOGO + BOX RISPOSTA LLM
# ----------------------------------------------------------------------
col_logo, col_llm = st.columns([1, 5], gap="large")

with col_logo:
    st.markdown('<div class="logo-box">A</div>', unsafe_allow_html=True)

with col_llm:
    st.markdown(
        f'<div class="llm-box">{api_client.turn_message(current_turn)}</div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# AREA RISPOSTA UTENTE
# ----------------------------------------------------------------------
st.markdown('<div class="label-rispondi">Rispondi</div>', unsafe_allow_html=True)

risposta_utente = st.text_area(
    label="La tua risposta",
    placeholder="Scrivi qui la tua risposta...",
    height=140,
    label_visibility="collapsed",
    key="input_risposta",
    disabled=is_closed,
)


# ----------------------------------------------------------------------
# RIGA INFERIORE: SEGNALINO VALUTAZIONE (SX) + PULSANTE PROCEDI (DX)
# ----------------------------------------------------------------------
col_segnalino, col_spacer, col_bottone = st.columns([2, 3, 1], gap="large")

with col_segnalino:
    is_meaningful = current_turn.get("is_meaningful") or {}
    if is_meaningful.get("azione") == "blocca":
        st.markdown(
            '<div class="fase-badge" style="background:#ffc9c9;">❌ Risposta non adeguata</div>',
            unsafe_allow_html=True,
        )
        st.caption(is_meaningful.get("motivazione", "Nessuna motivazione fornita."))
    elif current_turn.get("evaluation_of_previous_answer") is not None:
        ev = current_turn["evaluation_of_previous_answer"]
        st.markdown(
            f'<div class="fase-badge" style="background:#c8f7c5;">'
            f'✅ Valutazione: {ev.get("score", "—")}/3</div>',
            unsafe_allow_html=True,
        )
        st.caption(ev.get("comment", ""))
    else:
        st.markdown(
            '<div class="fase-badge">⏳ In attesa di valutazione…</div>',
            unsafe_allow_html=True,
        )

with col_bottone:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    procedi = st.button(
        "Procedi ➜",
        use_container_width=True,
        type="primary",
        disabled=is_closed,
    )


# ----------------------------------------------------------------------
# GESTIONE PULSANTE PROCEDI
# ----------------------------------------------------------------------
if procedi:
    if is_closed:
        st.warning("Il colloquio è concluso.")
    elif not risposta_utente.strip():
        st.warning("Scrivi una risposta prima di procedere.")
    else:
        try:
            response = api_client.interview(
                history=st.session_state["interview_history"],
                last_turn=st.session_state["interview_turn"],
                candidate_answer=risposta_utente.strip(),
            )
        except BackendApiError as error:
            st.error(str(error))
        else:
            st.session_state["interview_turn"] = response["turn"]
            st.session_state["interview_history"] = response["history"]
            st.session_state["interview_closed"] = response["is_closed"]
            st.rerun()
