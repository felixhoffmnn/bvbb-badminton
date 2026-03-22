import streamlit as st

from bvbb.frontend.data_store import get_store


def render() -> None:
    store = get_store()
    championship_code = st.session_state.get("championship_code")

    st.header("Spielerprofil")

    if not championship_code:
        st.info("Bitte eine Meisterschaft auswählen.")
        return

    query = st.text_input("Spieler suchen", placeholder="Name eingeben (mind. 2 Zeichen)")

    if not query or len(query) < 2:
        st.info("Bitte mindestens 2 Zeichen eingeben.")
        return

    results = store.search_players(query, championship_code)

    if not results:
        st.warning("Keine Spieler gefunden.")
        return

    options = {f"{name} ({club or 'Kein Verein'})": pid for pid, name, club in results}
    selected = st.selectbox("Spieler wählen", list(options.keys()))

    if not selected:
        return

    person_id = options[selected]

    try:
        player = store.get_player(person_id, championship_code)
    except KeyError:
        st.error("Spieler nicht gefunden.")
        return

    st.divider()
    st.subheader(player.name)
    if player.club:
        st.caption(player.club)

    s = player.stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Einzel", f"{s.singles_wins}:{s.singles_losses}")
    col2.metric("Doppel", f"{s.doubles_wins}:{s.doubles_losses}")
    col3.metric("Mixed", f"{s.mixed_wins}:{s.mixed_losses}")

    if player.match_history:
        st.markdown("**Spielhistorie**")
        data = []
        for m in player.match_history:
            data.append(
                {
                    "Datum": m.date or "",
                    "Disziplin": m.discipline,
                    "Gegner": ", ".join(m.opponents),
                    "Sätze": m.sets,
                    "Ergebnis": "Sieg" if m.won else "Niederlage",
                }
            )
        st.dataframe(data, width="stretch", hide_index=True)
