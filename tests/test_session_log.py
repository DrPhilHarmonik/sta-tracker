import db
import export


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_empty_log_writes_header_with_zero_count(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    out = tmp_path / "Session Log.md"
    count = export.export_session_log(out)
    assert count == 0
    text = out.read_text(encoding="utf-8")
    assert "# Campaign Session Log" in text
    assert "*0 sessions" in text


def test_sessions_render_in_timeline_order_with_metadata(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.create_entity("session", "The Reveal", {"session_number": "2", "stardate": "47990.2"},
                     "The saboteur is unmasked.")
    db.create_entity("session", "Arrival",
                     {"session_number": "1", "stardate": "47988.1", "location": "Starbase 12"},
                     "The crew arrives.")
    out = tmp_path / "log.md"
    count = export.export_session_log(out)
    assert count == 2
    text = out.read_text(encoding="utf-8")
    # ordered: session 1 before session 2
    assert text.index("Session 1: Arrival") < text.index("Session 2: The Reveal")
    assert "**Stardate** 47988.1" in text
    assert "**Location** [[Starbase 12]]" in text
    assert "The crew arrives." in text


def test_participants_listed_as_wikilinks(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    sid = db.create_entity("session", "First Contact", {"session_number": "1"}, "notes")
    npc_id = db.create_entity("npc", "Ambassador Sarek", {}, "")
    db.create_relationship(sid, npc_id, "involves", "")
    out = tmp_path / "log.md"
    export.export_session_log(out)
    text = out.read_text(encoding="utf-8")
    assert "**Featuring:** [[Ambassador Sarek]]" in text


def test_session_without_notes_marks_no_log(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.create_entity("session", "Placeholder", {"session_number": "1"}, "")
    out = tmp_path / "log.md"
    export.export_session_log(out)
    assert "*No log recorded.*" in out.read_text(encoding="utf-8")
