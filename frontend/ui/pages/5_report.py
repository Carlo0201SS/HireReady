import html
from pathlib import Path

import streamlit as st

from frontend.api_client import BackendApiError, api_client


st.set_page_config(
	page_title="HireReady | Report",
	page_icon="📊",
	layout="wide",
)

st.markdown(
	"""
	<style>
	.report-title { color: #1f3a5f; font-size: 2.2rem; font-weight: 750; }
	.report-summary {
		background: linear-gradient(135deg, #eef3f9, #f8fbff);
		border: 1px solid #dce6f1; border-left: 5px solid #4a7fb5;
		border-radius: 12px; padding: 22px 26px; margin: 18px 0 28px;
		color: #1f2d3d; line-height: 1.65; white-space: pre-wrap;
	}
	.answer-card {
		border: 1px solid #dce3eb; border-radius: 12px; padding: 20px 24px;
		margin: 14px 0; background: #fff; box-shadow: 0 2px 8px #1f3a5f12;
		color: #243447; line-height: 1.6;
	}
	.answer-card h3 { margin: 0 0 12px; color: #1f3a5f; }
	.answer-label { font-weight: 700; color: #4a6078; margin-top: 12px; }
	.answer-score {
		display: inline-block; border-radius: 20px; padding: 4px 12px;
		background: #e8f1fb; color: #1f3a5f; font-weight: 700;
	}
	</style>
	""",
	unsafe_allow_html=True,
)

st.markdown('<div class="report-title">Report del colloquio</div>', unsafe_allow_html=True)

history = st.session_state.get("interview_history")
current_turn = st.session_state.get("interview_turn")
if not history or not current_turn:
	st.info("Non è disponibile un colloquio da riepilogare.")
	st.page_link(
		str(Path(__file__).resolve().with_name("4_interview.py")),
		label="Vai al colloquio",
	)
	st.stop()

if not st.session_state.get("interview_closed", False):
	st.info("Il report sarà disponibile al termine del colloquio.")
	st.page_link(
		str(Path(__file__).resolve().with_name("4_interview.py")),
		label="Torna al colloquio",
	)
	st.stop()

report = st.session_state.get("interview_report")
if report is None:
	contenuto = (current_turn.get("is_meaningful") or {}).get("motivazione", "")
	with st.spinner("Gemma sta preparando il riepilogo del colloquio..."):
		try:
			report = api_client.generate_report(
				history=history,
				contenuto=contenuto,
				answers=st.session_state.get("interview_report_answers", []),
				score=st.session_state.get("score_response")
			)
		except BackendApiError as error:
			st.error(str(error))
			if st.button("Riprova"):
				st.rerun()
			st.stop()
	st.session_state["interview_report"] = report

summary = html.escape(report.get("summary", "Riepilogo non disponibile."))
st.markdown(
	f'<section class="report-summary"><strong>In sintesi</strong><br>{summary}</section>',
	unsafe_allow_html=True,
)

answers = report.get("answers", [])
st.subheader("Valutazione delle risposte")
if not answers:
	st.info("Non sono presenti risposte valutabili nel report.")

for index, item in enumerate(answers, start=1):
	score = item.get("score", 0)
	if score <= 4:
		criticita = "Risposta da approfondire"
	elif score <= 7:
		criticita = "Risposta parzialmente efficace"
	else:
		criticita = "Risposta solida"
	question = html.escape(item.get("question", ""))
	answer = html.escape(item.get("answer", ""))
	motivation = html.escape(item.get("motivation", ""))
	st.markdown(
		f"""
		<article class="answer-card">
			<h3>Risposta {index}
				<span class="answer-score">{score}/10 · {criticita}</span>
			</h3>
			<div class="answer-label">Domanda</div>
			<div>{question}</div>
			<div class="answer-label">Risposta del candidato</div>
			<div>{answer}</div>
			<div class="answer-label">Motivazione / criticità</div>
			<div>{motivation}</div>
		</article>
		""",
		unsafe_allow_html=True,
	)

if st.button("Torna al colloquio"):
	st.switch_page(str(Path(__file__).resolve().with_name("4_interview.py")))
