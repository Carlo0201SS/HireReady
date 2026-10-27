import streamlit as st
import os
from pathlib import Path

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
FASE_CORRENTE = st.session_state.get("fase", 1)   # 1, 2 o 3
TITOLO_FONT_SIZE = 42                              # <- regolabile (px)
TITOLO_TEMPLATE = "Colloquio fase {fase}"          # <- regolabile
MAX_FASI = 3

# Inizializzazione stato sessione
if "fase" not in st.session_state:
    st.session_state.fase = 1
if "risposta_llm" not in st.session_state:
    st.session_state.risposta_llm = (
        "Ciao! Sono l'assistente virtuale. Quando sei pronto, "
        "iniziamo con la prima domanda del colloquio."
    )
if "cronologia" not in st.session_state:
    st.session_state.cronologia = []

FASE_CORRENTE = st.session_state.fase
TITOLO = TITOLO_TEMPLATE.format(fase=FASE_CORRENTE)

# ----------------------------------------------------------------------
# CSS PERSONALIZZATO
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    /* Titolo centrale con dimensione parametrica */
    .titolo-centrale {{
        text-align: center;
        font-size: {TITOLO_FONT_SIZE}px;
        font-weight: 700;
        color: #1f3a5f;
        margin-top: 10px;
        margin-bottom: 40px;
        font-family: 'Segoe UI', sans-serif;
    }}

    /* Logo "A" */
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
        margin-left: 40px;      /* separazione dal margine sinistro */
        margin-top: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        font-family: 'Georgia', serif;
    }}

    /* Box risposta LLM */
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
    }}

    /* Etichetta Rispondi */
    .label-rispondi {{
        font-size: 20px;
        font-weight: 600;
        color: #1f3a5f;
        margin-top: 30px;
        margin-bottom: 8px;
    }}

    /* Segnalino grafico fase */
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
# TITOLO CENTRALE
# ----------------------------------------------------------------------
st.markdown(f'<div class="titolo-centrale">{TITOLO}</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------
# RIGA: LOGO + BOX RISPOSTA LLM
# ----------------------------------------------------------------------
col_logo, col_llm = st.columns([1, 5], gap="large")

with col_logo:
    st.markdown('<div class="logo-box">A</div>', unsafe_allow_html=True)

with col_llm:
    st.markdown(
        f'<div class="llm-box">{st.session_state.risposta_llm}</div>',
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
)

# ----------------------------------------------------------------------
# RIGA INFERIORE: SEGNALINO FASE (SX) + PULSANTE PROCEDI (DX)
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# RIGA INFERIORE: SEGNALINO VALUTAZIONE (SX) + PULSANTE PROCEDI (DX)
# ----------------------------------------------------------------------
col_segnalino, col_spacer, col_bottone = st.columns([2, 3, 1], gap="large")

with col_segnalino:
    valutazione = st.session_state.get("valutazione_llm", None)

    # Nessuna valutazione ancora disponibile
    if valutazione is None:
        st.markdown(
            '<div class="fase-badge">⏳ In attesa di valutazione…</div>',
            unsafe_allow_html=True,
        )
    else:
        stato = valutazione.get("valutazione", "").lower()

        # ---------- CASO 1: RISPOSTA BUONA ----------
        if stato == "buona":
            img_ok = Path("assets") / "spunta_verde.png"
            if img_ok.exists():
                st.image(str(img_ok), width=90)
            else:
                st.markdown(
                    '<div class="fase-badge" style="background:#c8f7c5;">✅ Risposta buona</div>',
                    unsafe_allow_html=True,
                )

        # ---------- CASO 2: RISPOSTA CON DIFETTI ----------
        elif stato == "difetti":
            img_dif = Path("assets") / "emoji_pensante.png"
            if img_dif.exists():
                st.image(str(img_dif), width=90)
            else:
                st.markdown(
                    '<div class="fase-badge" style="background:#ffe9a8;">🤔 Risposta con difetti</div>',
                    unsafe_allow_html=True,
                )

            # Selectbox con l'elenco dei problemi individuati dal modello
            problemi = valutazione.get("problemi", [])
            if problemi:
                st.selectbox(
                    "Problema individuato:",
                    options=problemi,
                    key=f"problema_fase_{FASE_CORRENTE}",
                )
            else:
                st.caption("Nessun dettaglio sui difetti fornito dal modello.")

        # ---------- CASO 3: RISPOSTA NEGATIVA (etica) ----------
        elif stato == "negativa":
            img_neg = Path("assets") / "croce_rossa.png"
            if img_neg.exists():
                st.image(str(img_neg), width=90)
            else:
                st.markdown(
                    '<div class="fase-badge" style="background:#ffc9c9;">❌ Risposta non adeguata</div>',
                    unsafe_allow_html=True,
                )

            # Selectbox con la spiegazione dell'inadeguatezza etica
            spiegazioni = valutazione.get("spiegazione", [])
            if spiegazioni:
                st.selectbox(
                    "Motivazione:",
                    options=spiegazioni,
                    key=f"spiegazione_fase_{FASE_CORRENTE}",
                )
            else:
                st.caption("Nessuna spiegazione fornita dal modello.")

        # ---------- CASO FALLBACK ----------
        else:
            st.markdown(
                f'<div class="fase-badge">⚠️ Stato non riconosciuto: {stato}</div>',
                unsafe_allow_html=True,
            )

with col_bottone:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    procedi = st.button("Procedi ➜", use_container_width=True, type="primary")

# ----------------------------------------------------------------------
# GESTIONE PULSANTE PROCEDI
# ----------------------------------------------------------------------
if procedi:
    if risposta_utente.strip():
        # Salva nella cronologia
        st.session_state.cronologia.append(
            {"fase": FASE_CORRENTE, "risposta": risposta_utente.strip()}
        )

        # --- QUI andrebbe la chiamata all'LLM ---
        # Esempio fittizio: la risposta LLM viene aggiornata
        st.session_state.risposta_llm = (
            f"Ricevuto per la fase {FASE_CORRENTE}: "
            f"«{risposta_utente.strip()[:80]}...». "
            f"Passiamo alla fase successiva."
        )

        # Avanza di fase (fino a MAX_FASI)
        if st.session_state.fase < MAX_FASI:
            st.session_state.fase += 1

        st.rerun()
    else:
        st.warning("Per favore, scrivi una risposta prima di procedere.")

# ----------------------------------------------------------------------
# (OPZIONALE) CRONOLOGIA IN ESPANSIONE
# ----------------------------------------------------------------------
if st.session_state.cronologia:
    with st.expander("📜 Cronologia risposte"):
        for i, item in enumerate(st.session_state.cronologia, 1):
            st.write(f"**{i}. Fase {item['fase']}** — {item['risposta']}")
