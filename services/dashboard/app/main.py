import streamlit as st

st.set_page_config(
    page_title="Temperature Logger",
    page_icon="🌡️",
    layout="wide",
)

st.title("🌡️ Temperature Logger")
st.markdown("Use the sidebar to navigate between pages.")

col1, col2, col3, col4 = st.columns(4)
col1.info("**🌡 Temperature**\nLive readings + test")
col2.info("**⚙ Pressure**\nLive readings + test")
col3.info("**🏭 Machines**\nRegister machines")
col4.info("**📅 History**\nBrowse past tests")
