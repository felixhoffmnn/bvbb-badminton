import streamlit as st

from bvbb.frontend.data_store import get_store
from bvbb.frontend.pages import spieler, uebersicht, verein

st.set_page_config(page_title="BVBB Badminton Liga", layout="wide")

pg = st.navigation(
    [
        st.Page(uebersicht.render, title="Übersicht", icon=":material/trophy:", default=True, url_path="uebersicht"),
        st.Page(spieler.render, title="Spieler", icon=":material/person_search:", url_path="spieler"),
        st.Page(verein.render, title="Verein", icon=":material/location_city:", url_path="verein"),
    ]
)

with st.sidebar:
    st.title("BVBB Liga")

    store = get_store()
    championships = store.list_championships()
    if championships:
        selected = st.selectbox("Meisterschaft", championships)
        st.session_state["championship_code"] = selected
    else:
        st.warning("Keine Daten. Bitte `bvbb-crawl` ausführen.")

pg.run()
