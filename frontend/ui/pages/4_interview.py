import html
from pathlib import Path

import streamlit as st
from fastapi import HTTPException

from frontend.api_client import api_client


# ----------------------------------------------------------------------
# CONFIGURAZIONE PAGINA
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="HireReady | Colloquio",
    page_icon="💬",
    layout="wide",
)


# ----------------------------------------------------------------------
# FASI DEL COLLOQUIO (allineate a HireReadyTurn.phase)
# ----------------------------------------------------------------------
FASI = {
    "cv": (1, "Esperienze e CV"),
    "carriera": (2, "Carriera e integrazione con il ruolo"),
    "tecnica": (3, "Domande tecniche"),
    "finale": (4, "Chiusura"),
}
TOTALE_FASI = len(FASI)


# ----------------------------------------------------------------------
# CSS PERSONALIZZATO
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .progress-fase {
        font-size: 15px;
        font-weight: 600;
        color: #4a7fb5;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }
    .titolo-pagina {
        font-size: 30px;
        font-weight: 700;
        color: #1f3a5f;
        line-height: 1.25;
        margin-bottom: 28px;
    }
    .avatar-box {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 72px;
        height: 72px;
        background: linear-gradient(135deg, #1f3a5f, #4a7fb5);
        color: white;
        font-size: 34px;
        font-weight: bold;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        font-family: 'Georgia', serif;
    }
    .avatar-label {
        font-size: 13px;
        color: #5b6b7d;
        margin-top: 6px;
    }
    .llm-box {
        background-color: #eef3f9;
        border-left: 5px solid #4a7fb5;
        padding: 18px 22px;
        border-radius: 8px;
        font-size: 17px;
        color: #1f2d3d;
        min-height: 72px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        white-space: pre-wrap;
    }
    .label-rispondi {
        font-size: 18px;
        font-weight: 600;
        color: #1f3a5f;
        margin-top: 28px;
        margin-bottom: 8px;
    }
    .fase-badge {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 12px;
        color: #333;
        font-weight: 400;
        margin-top: 6px;
    }
    .fase-badge--blocked {
        background-color: #ffc9c9;
    }
    .fase-badge--score {
        background-color: #c8f7c5;
    }
    .briefing-box {
        background-color: #f6f8fb;
        border: 1px solid #dde5ef;
        border-radius: 10px;
        padding: 22px 26px;
        color: #1f2d3d;
        font-size: 16px;
        line-height: 1.6;
    }
    .briefing-box h4 { color: #1f3a5f; margin: 14px 0 6px 0; }
    .briefing-box h4:first-child { margin-top: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# GUARDIA: contesto presente?
# ----------------------------------------------------------------------
context = st.session_state.get("cv_interview_context")
level_position = st.session_state.get("level_position")
if not context or level_position not in {"junior", "middle", "senior"}:
    st.info("Prima di iniziare il colloquio devi scegliere la posizione e il livello.")
    st.page_link(
        str(Path(__file__).resolve().with_name("4_level_position.py")),
        label="Vai alla scelta del livello",
    )
    st.stop()


# ----------------------------------------------------------------------
# BRIEFING INIZIALE — mostrato prima della prima domanda
# ----------------------------------------------------------------------
if "interview_turn" not in st.session_state:
    posizione = html.escape(str(context.get("selected_position", "—")))

    st.markdown('<div class="progress-fase">Prima di iniziare</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="titolo-pagina">Colloquio per: {posizione}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="briefing-box">
        <h4>Come funziona</h4>
        Il colloquio si svolge in 4 fasi: <b>esperienze e CV</b>,
        <b>carriera e integrazione con il ruolo</b>, <b>domande tecniche</b>
        e <b>chiusura</b>. Riceverai una domanda alla volta.

        <h4>Regole</h4>
        • Non c'è un timer: prenditi il tempo che ti serve per ogni risposta.<br>
        • Rispondi in modo completo e concreto, con esempi reali: le risposte vaghe ricevono un punteggio basso.<br>
        • Mantieni un linguaggio professionale: un linguaggio inappropriato chiude il colloquio.

        <h4>Alla fine</h4>
        Riceverai un report con punti di forza, aree di miglioramento e consigli.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    col_inizia, col_speech = st.columns([1, 3])
    with col_inizia:
        if st.button("Inizia il colloquio ➜", type="primary"):
            with st.spinner("Preparazione della prima domanda…"):
                try:
                    response = api_client.interview(
                        anonymized_cv=context["anonymized_cv"],
                        selected_position=context["selected_position"],
                        level_position=level_position,
                        position_description=context.get("position_description", ""),
                        profile=context["profile"],
                    )
                except HTTPException as error:
                    st.error(str(error.detail))
                    st.stop()
            st.session_state["interview_turn"] = response["turn"]
            st.session_state["interview_history"] = response["history"]
            st.session_state["interview_closed"] = (
                response["is_closed"]
                or api_client.is_interview_closed(response["turn"])
            )
            st.session_state["interview_report_answers"] = []
            st.session_state.pop("interview_report", None)
            st.session_state["answer_counter"] = 0
            st.rerun()
    with col_speech:
        st.button("speech to text", type="primary")
    st.stop()


current_turn = st.session_state["interview_turn"]
is_closed = st.session_state.get("interview_closed", False)


# ----------------------------------------------------------------------
# INTESTAZIONE: AVANZAMENTO FASE
# ----------------------------------------------------------------------
numero_fase, nome_fase = FASI.get(current_turn.get("phase"), (None, "Colloquio"))
avanzamento = (
    f"Fase {numero_fase} di {TOTALE_FASI}" if numero_fase else "Colloquio"
)
st.markdown(f'<div class="progress-fase">{avanzamento}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="titolo-pagina">{nome_fase}</div>', unsafe_allow_html=True)
if numero_fase:
    st.progress(numero_fase / TOTALE_FASI)


# ----------------------------------------------------------------------
# RIGA: AVATAR INTERVISTATORE + DOMANDA
# ----------------------------------------------------------------------
col_avatar, col_llm = st.columns([1, 9], gap="medium")

with col_avatar:
    st.markdown(
        '<div class="avatar-box">H</div><div class="avatar-label">Intervistatore</div>',
        unsafe_allow_html=True,
    )

with col_llm:
    messaggio = html.escape(api_client.turn_message(current_turn))
    st.markdown(f'<div class="llm-box">{messaggio}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------
# VALUTAZIONE DELLA RISPOSTA PRECEDENTE (solo se esiste)
# ----------------------------------------------------------------------
is_meaningful = current_turn.get("is_meaningful") or {}
if is_meaningful.get("azione") == "blocca":
    evaluation = current_turn.get("evaluation_of_previous_answer") or {}
    score = evaluation.get("score")
    score_text = f" · {score}/10" if score is not None else ""
    st.markdown(
        f'<div class="fase-badge fase-badge--blocked">'
        f'❌ Risposta non adeguata{score_text}</div>',
        unsafe_allow_html=True,
    )
elif current_turn.get("evaluation_of_previous_answer") is not None:
    ev = current_turn["evaluation_of_previous_answer"]
    st.markdown(
        f'<div class="fase-badge fase-badge--score">'
        f'✅ Risposta precedente: {ev.get("score", "—")}/10</div>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# AREA RISPOSTA UTENTE
# ----------------------------------------------------------------------
if is_closed:
    is_normal_final_turn = api_client.is_final_turn(current_turn)
    if is_normal_final_turn and is_meaningful.get("azione") != "blocca":
        st.success("Grazie per aver partecipato al colloquio!")
    elif current_turn.get("closure_reason") == "profile_contradiction":
        st.warning(api_client.turn_message(current_turn))
    else:
        st.info("Il colloquio è concluso.")
    if st.button("Visualizza report del colloquio ➜", type="primary"):
        st.switch_page(str(Path(__file__).resolve().with_name("5_report.py")))
    st.stop()

st.markdown('<div class="label-rispondi">La tua risposta</div>', unsafe_allow_html=True)

risposta_utente = st.text_area(
    label="La tua risposta",
    placeholder="Scrivi qui la tua risposta…",
    height=160,
    label_visibility="collapsed",
    # Chiave diversa per ogni domanda: così la casella riparte vuota.
    key=f"input_risposta_{st.session_state.get('answer_counter', 0)}",
)

_, col_bottone = st.columns([5, 1])
with col_bottone:
    invia = st.button("Invia risposta ➜", use_container_width=True, type="primary")


# ----------------------------------------------------------------------
# INVIO RISPOSTA
# ----------------------------------------------------------------------
if invia:
    if not risposta_utente.strip():
        st.warning("Scrivi una risposta prima di inviarla.")
    else:
        with st.spinner("Valutazione della risposta in corso…"):
            try:
                previous_turn = st.session_state["interview_turn"]
                response = api_client.interview(
                    history=st.session_state["interview_history"],
                    anonymized_cv=context["anonymized_cv"],
                    last_turn=previous_turn,
                    candidate_answer=risposta_utente.strip(),
                )
            except HTTPException as error:
                st.error(str(error.detail))
                st.stop()
        evaluated_turn = response["turn"]
        next_question = previous_turn.get("next_question") or {}
        evaluation = evaluated_turn.get("evaluation_of_previous_answer") or {}
        meaningful = evaluated_turn.get("is_meaningful") or {}
        if next_question.get("text"):
            answers = st.session_state.setdefault("interview_report_answers", [])
            answers.append(
                {
                    "question": next_question["text"],
                    "answer": risposta_utente.strip(),
                    "motivation": meaningful.get(
                        "motivazione",
                        "Risposta non valutata prima della chiusura.",
                    ),
                    "score": evaluation.get("score"),
                }
            )

        st.session_state["interview_turn"] = evaluated_turn
        st.session_state["interview_history"] = response["history"]
        st.session_state["interview_closed"] = (
            response["is_closed"] or api_client.is_interview_closed(evaluated_turn)
        )
        st.session_state["answer_counter"] = st.session_state.get("answer_counter", 0) + 1
        st.rerun()
