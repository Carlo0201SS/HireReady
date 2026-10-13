import streamlit as st


st.set_page_config(page_title="HireReady | Carica CV", layout="wide")

upload_page = st.Page("src/ui/pages/1_upload_cv.py", title="Carica CV", default=True)
navigation = st.navigation([upload_page])
navigation.run()
