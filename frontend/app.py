from pathlib import Path
import sys

import streamlit as st

FRONTEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRONTEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))


st.set_page_config(
	page_title="HireReady",
	layout="wide",
	initial_sidebar_state="collapsed",
)
st.markdown(
	"""
	<style>
	[data-testid="stSidebar"],
	[data-testid="stSidebarCollapsedControl"] {
		display: none;
	}
	/* Contenuto centrato: su schermi larghi le righe non diventano infinite */
	.block-container { max-width: 1100px; padding-top: 2.5rem; }
	/* Intestazione comune delle pagine (stesse classi della pagina Colloquio) */
	.progress-fase {
		font-size: 15px; font-weight: 600; color: #4a7fb5;
		text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px;
	}
	.titolo-pagina {
		font-size: 30px; font-weight: 700; color: #1f3a5f;
		line-height: 1.25; margin-bottom: 8px;
	}
	.sottotitolo-pagina { font-size: 16px; color: #5b6b7d; margin-bottom: 24px; }
	.stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 600; }

	/* Testata, uguale in tutte le pagine */
	.testata { padding-bottom: 22px; margin-bottom: 30px; border-bottom: 1px solid #dde5ef; }
	.testata-marchio {
		font-size: 14px; font-weight: 700; color: #4a7fb5;
		text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;
	}
	.testata-titolo { font-size: 36px; font-weight: 800; line-height: 1.15; color: #1f3a5f; margin-bottom: 8px; }
	.testata-titolo span { color: #4a7fb5; }
	.testata-sottotitolo { font-size: 16px; line-height: 1.6; color: #5b6b7d; max-width: 760px; }

	/* Percorso in 5 passi, in fondo a ogni pagina */
	.percorso {
		display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
		font-size: 14px; color: #5b6b7d;
		border-top: 1px solid #dde5ef; margin-top: 40px; padding-top: 18px;
	}
	.percorso-passo { display: flex; align-items: center; gap: 8px; }
	.percorso-numero {
		display: inline-flex; align-items: center; justify-content: center;
		width: 24px; height: 24px; border-radius: 50%;
		background-color: #eef3f9; color: #1f3a5f; font-weight: 700; font-size: 13px;
	}
	.percorso-passo--fatto .percorso-numero { background-color: #c8f7c5; color: #1e5631; }
	.percorso-passo--attivo { color: #1f3a5f; font-weight: 600; }
	.percorso-passo--attivo .percorso-numero { background-color: #1f3a5f; color: #ffffff; }
	.percorso-freccia { color: #b8c6d6; }

	/* Riquadro chiaro per i contenuti principali: st.container(key="riquadro_...") */
	[class*="st-key-riquadro"] {
		background-color: #f6f8fb; border: 1px solid #dde5ef; border-radius: 12px;
		padding: 24px 26px; box-shadow: 0 2px 8px rgba(31, 58, 95, 0.08);
	}
	</style>
	""",
	unsafe_allow_html=True,
)

upload_page = st.Page(
	str(FRONTEND_DIR / "ui" / "pages" / "1_upload_cv.py"),
	title="Carica CV",
	default=True,
)
position_page = st.Page(
	str(FRONTEND_DIR / "ui" / "pages" / "3_choice_position.py"),
	title="Posizione",
)
level_page = st.Page(
	str(FRONTEND_DIR / "ui" / "pages" / "4_level_position.py"),
	title="Livello",
)
interview_page = st.Page(
	str(FRONTEND_DIR / "ui" / "pages" / "4_interview.py"),
	title="Colloquio",
)
report_page = st.Page(
	str(FRONTEND_DIR / "ui" / "pages" / "5_report.py"),
	title="Report",
)
pagine = [upload_page, position_page, level_page, interview_page, report_page]
navigation = st.navigation(pagine, position="hidden")

# Struttura di ogni pagina: testata, corpo (la pagina vera e propria), percorso in fondo.
# I contenitori vengono creati in quest'ordine, quindi il percorso resta sotto
# anche se la pagina si interrompe con st.stop().
testata = st.container()
corpo = st.container()
fondo = st.container()

testata.markdown(
	"""
	<div class="testata">
		<div class="testata-marchio">HireReady</div>
		<div class="testata-titolo">Allenati al colloquio, <span>prima del colloquio.</span></div>
		<div class="testata-sottotitolo">
			Carica il CV, scegli ruolo e livello: un intervistatore AI ti fa le domande,
			valuta ogni risposta e alla fine ti dà un report con punti di forza e cosa migliorare.
		</div>
	</div>
	""",
	unsafe_allow_html=True,
)

# Percorso: il passo della pagina corrente è evidenziato, quelli prima hanno la spunta
indice_corrente = [pagina.title for pagina in pagine].index(navigation.title)
elementi = []
for indice, pagina in enumerate(pagine):
	if indice < indice_corrente:
		stato, simbolo = " percorso-passo--fatto", "✓"
	elif indice == indice_corrente:
		stato, simbolo = " percorso-passo--attivo", str(indice + 1)
	else:
		stato, simbolo = "", str(indice + 1)
	if indice > 0:
		elementi.append('<span class="percorso-freccia">→</span>')
	elementi.append(
		f'<span class="percorso-passo{stato}"><span class="percorso-numero">{simbolo}</span>{pagina.title}</span>'
	)
fondo.markdown(f'<div class="percorso">{"".join(elementi)}</div>', unsafe_allow_html=True)

with corpo:
	navigation.run()
