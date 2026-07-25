import db
import timeline


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_timeline_starts_empty(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert timeline.session_entries() == []


def test_entries_ordered_by_session_number(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.create_entity("session", "Third", {"session_number": "3"}, "")
    db.create_entity("session", "First", {"session_number": "1"}, "")
    db.create_entity("session", "Second", {"session_number": "2"}, "")
    assert [e["name"] for e in timeline.session_entries()] == ["First", "Second", "Third"]


def test_unnumbered_sessions_sort_after_numbered(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.create_entity("session", "Prologue", {}, "")
    db.create_entity("session", "One", {"session_number": "1"}, "")
    assert [e["name"] for e in timeline.session_entries()] == ["One", "Prologue"]


def test_recap_is_first_non_blank_note_line(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.create_entity("session", "S1", {"session_number": "1"},
                     "\n   \nThe crew beams down to Erevos.\nMore text.")
    entry = timeline.session_entries()[0]
    assert entry["recap"] == "The crew beams down to Erevos."


def test_entry_carries_stardate_and_location(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.create_entity("session", "S1",
                     {"session_number": "1", "stardate": "47988.1", "location": "Starbase 12"}, "")
    entry = timeline.session_entries()[0]
    assert entry["stardate"] == "47988.1"
    assert entry["location"] == "Starbase 12"
    assert entry["recap"] == ""
