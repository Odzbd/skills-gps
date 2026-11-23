from skills_gps.text import boilerplate, is_english, to_lines


def test_lines_split_on_blocks_and_unescape_entities():
    assert to_lines("<p>R&amp;D</p><ul><li>Python <b>3</b></li></ul>") == ["R&D", "Python 3"]


def test_greenhouse_escaped_html_is_decoded():
    assert to_lines("&lt;p&gt;Excel &amp;amp; SQL&lt;/p&gt;") == ["Excel & SQL"]


def test_english_detection():
    assert is_english(["You will work with the team to build our products for the web"])
    assert not is_english(["Wir suchen einen erfahrenen Entwickler mit Kenntnissen in Python"])
    assert not is_english(["물류 인프라 담당자를 모집합니다 저희 팀과 성장할 분 Python"])
    assert not is_english([])


def test_boilerplate_needs_many_titles_and_a_long_line():
    long = "We build payment infrastructure for companies all over the world"
    jobs = [(f"Role {i}", [long, "Python"]) for i in range(5)]
    assert boilerplate(jobs) == {long}
    assert boilerplate([("Same role", [long])] * 5) == set()
