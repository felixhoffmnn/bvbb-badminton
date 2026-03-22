from datetime import date

from bvbb.scraper.parser import (
    extract_int_param,
    extract_param,
    find_table_by_header,
    make_soup,
    parse_german_date,
    parse_score,
    safe_int,
)


def test_find_table_by_header():
    html = """
    <table>
      <tr><th>Name</th><th>Value</th></tr>
      <tr><td>A</td><td>1</td></tr>
    </table>
    <table>
      <tr><th>Rang</th><th>Team</th></tr>
      <tr><td>1</td><td>X</td></tr>
    </table>
    """
    soup = make_soup(html)
    table = find_table_by_header(soup, "Rang")
    assert table is not None
    assert "X" in table.get_text()
    assert find_table_by_header(soup, "Missing") is None


def test_parse_german_date():
    assert parse_german_date("Sa. 20.09.2025") == date(2025, 9, 20)
    assert parse_german_date("18.10.2025 some text") == date(2025, 10, 18)
    assert parse_german_date("no date here") is None


def test_safe_int():
    assert safe_int("42") == 42
    assert safe_int("abc") is None
    assert safe_int("") is None


def test_extract_param():
    url = "/wa/groupPage?championship=BBMM+25%2F26&group=38016"
    assert extract_param(url, "group") == "38016"
    assert extract_param(url, "championship") == "BBMM 25/26"
    assert extract_param(url, "missing") is None


def test_extract_int_param():
    url = "/wa/playerPortrait?person=1131771&club=10951"
    assert extract_int_param(url, "person") == 1131771
    assert extract_int_param(url, "club") == 10951
    assert extract_int_param(url, "missing") is None


def test_parse_score():
    assert parse_score("21:15") == (21, 15)
    assert parse_score("3:5") == (3, 5)
    assert parse_score("") is None
    assert parse_score("abc") is None
