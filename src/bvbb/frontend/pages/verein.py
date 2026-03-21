import streamlit as st

from bvbb.frontend.data_store import get_store


def render() -> None:
    store = get_store()
    championship_code = st.session_state.get("championship_code")

    st.header("Vereinsinformationen")

    if not championship_code:
        st.info("Bitte eine Meisterschaft auswählen.")
        return

    query = st.text_input("Verein suchen", placeholder="Name eingeben (mind. 2 Zeichen)")

    if not query or len(query) < 2:
        st.info("Bitte mindestens 2 Zeichen eingeben.")
        return

    results = store.search_clubs(query, championship_code)

    if not results:
        st.warning("Keine Vereine gefunden.")
        return

    options = {name: cid for cid, name in results}
    selected = st.selectbox("Verein wählen", list(options.keys()))

    if not selected:
        return

    club_id = options[selected]

    try:
        club = store.get_club(club_id, championship_code)
    except KeyError:
        st.error("Verein nicht gefunden.")
        return

    st.divider()
    st.subheader(club.name)

    if club.website:
        st.markdown(f"[Website]({club.website})")

    if club.venues:
        st.markdown("**Hallen:**")
        for v in club.venues:
            st.write(f"- {v}")

    if club.teams:
        st.markdown("**Mannschaften:**")
        data = [{"Team": t.team_name, "Liga": t.league or "-"} for t in club.teams]
        st.dataframe(data, width="stretch", hide_index=True)
