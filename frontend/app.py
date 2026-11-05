from pathlib import Path
import sys

import streamlit as st

FRONTEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRONTEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))


st.set_page_config(
	page_title="HireReady | Carica CV",
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
interview_page = st.Page(
	str(FRONTEND_DIR / "ui" / "pages" / "4_interview.py"),
	title="Colloquio",
)
report_page = st.Page(
	str(FRONTEND_DIR / "ui" / "pages" / "5_report.py"),
	title="Report",
)
navigation = st.navigation(
	[upload_page, position_page, interview_page, report_page],
	position="hidden",
)
navigation.run()
