import streamlit as st


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

upload_page = st.Page("frontend/ui/pages/1_upload_cv.py", title="Carica CV", default=True)
anonymization_page = st.Page("frontend/ui/pages/2_anonymization.py", title="Anonimizzazione")
navigation = st.navigation([upload_page, anonymization_page], position="hidden")
navigation.run()
