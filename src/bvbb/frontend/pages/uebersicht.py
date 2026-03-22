import streamlit as st

from bvbb.frontend.data_store import get_store


def render() -> None:
    store = get_store()
    championship_code = st.session_state.get("championship_code")
    group_id = st.session_state.get("group_id")

    if not championship_code:
        st.info("Bitte eine Meisterschaft auswählen.")
        return

    if group_id is not None:
        _render_group_detail(store, group_id, championship_code)
    else:
        _render_championship_overview(store, championship_code)


def _render_championship_overview(store, championship_code: str) -> None:
    st.header("Ligenplan")

    try:
        champ = store.get_championship(championship_code)
    except KeyError:
        st.error("Keine Daten gefunden. Bitte zuerst `bvbb-crawl` ausführen.")
        return

    category_names = [cat.category for cat in champ.categories]
    tabs = st.tabs(category_names)

    for tab, cat in zip(tabs, champ.categories, strict=True):
        with tab:
            cols = st.columns(3)
            for i, group in enumerate(cat.groups):
                with cols[i % 3], st.container(border=True):
                    st.markdown(f"**{group.name}**")

                    try:
                        standings = store.get_standings(group.group_id, championship_code)
                        team_count = len(standings.entries)
                        leader = standings.entries[0].team if standings.entries else "-"
                        st.caption(f"{team_count} Teams · Führend: {leader}")
                    except KeyError:
                        st.caption("Keine Daten")

                    if st.button("Anzeigen", key=f"show_{group.group_id}"):
                        st.session_state["group_id"] = group.group_id
                        st.rerun()


def _render_group_detail(store, group_id: int, championship_code: str) -> None:
    if st.button("← Alle Gruppen"):
        del st.session_state["group_id"]
        st.rerun()

    try:
        standings = store.get_standings(group_id, championship_code)
    except KeyError:
        st.error("Keine Tabellendaten vorhanden.")
        return

    st.header(standings.group_name or f"Gruppe {group_id}")

    tab_overview, tab_table, tab_schedule = st.tabs(["Übersicht", "Tabelle", "Spielplan"])

    with tab_overview:
        _render_overview_tab(standings)

    with tab_table:
        _render_table_tab(standings)

    with tab_schedule:
        _render_schedule_tab(store, group_id, championship_code)


def _render_overview_tab(standings) -> None:
    entries = standings.entries
    if not entries:
        st.info("Keine Tabellendaten vorhanden.")
        return

    leader = entries[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Teams", len(entries))
    col2.metric("Führend", leader.team)
    col3.metric("Punkte", leader.points)

    st.markdown("**Top 3**")
    for e in entries[:3]:
        st.write(f"{e.rank}. {e.team} — {e.points} Punkte")


def _render_table_tab(standings) -> None:
    if not standings.entries:
        st.info("Keine Tabellendaten vorhanden.")
        return

    data = []
    for e in standings.entries:
        data.append(
            {
                "#": e.rank,
                "Team": e.team,
                "Sp.": e.matches_played,
                "S": e.wins,
                "U": e.draws,
                "N": e.losses,
                "Punkte": e.points,
                "Spiele": e.games,
                "Sätze": e.sets,
            }
        )

    st.dataframe(data, width="stretch", hide_index=True)


def _render_schedule_tab(store, group_id: int, championship_code: str) -> None:
    try:
        schedule = store.get_schedule(group_id, championship_code)
    except KeyError:
        st.info("Keine Spielplandaten vorhanden.")
        return

    if not schedule:
        st.info("Keine Spielplandaten vorhanden.")
        return

    data = []
    for e in schedule:
        date_str = e.match_date.strftime("%d.%m.%Y") if e.match_date else ""
        time_str = e.match_time.strftime("%H:%M") if e.match_time else ""
        data.append(
            {
                "Datum": date_str,
                "Zeit": time_str,
                "Halle": e.venue or "",
                "Heim": e.home_team,
                "Gast": e.away_team,
                "Ergebnis": e.score or "-",
            }
        )

    st.dataframe(data, width="stretch", hide_index=True)

    matches_with_score = [e for e in schedule if e.score and e.meeting_id]
    if matches_with_score:
        st.subheader("Spielbericht")
        options = {f"{e.home_team} vs {e.away_team} ({e.score})": e for e in matches_with_score}
        selected = st.selectbox("Begegnung wählen", list(options.keys()))
        if selected:
            entry = options[selected]
            _render_match_report(store, entry.meeting_id, championship_code)


def _render_match_report(store, meeting_id: int, championship_code: str) -> None:
    try:
        report = store.get_match_report(meeting_id, championship_code)
    except KeyError:
        st.warning("Spielbericht nicht gefunden.")
        return

    date_str = report.match_date.strftime("%d.%m.%Y") if report.match_date else ""
    st.markdown(f"**{report.home_team} vs {report.away_team}**")
    st.caption(f"{date_str} | Ergebnis: {report.home_score}:{report.away_score}")

    if not report.disciplines:
        st.info("Keine Disziplinergebnisse vorhanden.")
        return

    data = []
    for d in report.disciplines:
        home = " / ".join(d.home_players)
        away = " / ".join(d.away_players)
        sets_str = ", ".join(f"{s.home}:{s.away}" for s in d.sets)
        data.append(
            {
                "Disziplin": d.discipline,
                "Heim": home,
                "Gast": away,
                "Sätze": sets_str,
                "Spiel": f"{d.home_match_point}:{d.away_match_point}",
            }
        )

    st.dataframe(data, width="stretch", hide_index=True)
