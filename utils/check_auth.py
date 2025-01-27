import streamlit as st

def check_auth():
    if not st.session_state.get("authenticated", False):
        st.error("Please login from the Home page")
        st.stop()
