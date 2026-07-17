import db
import talents
import focuses


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


# -- talents ------------------------------------------------------------------

def test_talents_library_ships_empty(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert talents.all_talents() == []
    assert talents.names() == []
    assert talents.find("Bold") is None


def test_talent_save_and_find(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    talents.save("Bold: Command", "Re-roll dice when you buy them with Threat.")
    found = talents.find("bold: command")
    assert found is not None
    assert found["description"].startswith("Re-roll")
    assert talents.names() == ["Bold: Command"]


def test_talent_save_upserts_by_name(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    talents.save("Studious", "old text")
    talents.save("studious", "new text")
    all_ = talents.all_talents()
    assert len(all_) == 1
    assert all_[0]["description"] == "new text"


def test_talent_blank_name_is_a_noop(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    talents.save("   ")
    assert talents.all_talents() == []


def test_talent_search_matches_name_and_description(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    talents.save("Bold: Command", "spend Threat")
    talents.save("Cautious: Security", "reduce complications")
    assert [t["name"] for t in talents.search("bold")] == ["Bold: Command"]
    assert [t["name"] for t in talents.search("complications")] == ["Cautious: Security"]


def test_talent_remove(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    talents.save("A")
    talents.save("B")
    talents.remove("A")
    assert talents.names() == ["B"]


# -- focuses ------------------------------------------------------------------

def test_focuses_library_ships_empty(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert focuses.all_focuses() == []


def test_focus_add_and_dedupe(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    focuses.add("Astrophysics")
    focuses.add("astrophysics")  # duplicate, case-insensitive
    focuses.add("  ")            # blank
    assert focuses.all_focuses() == ["Astrophysics"]


def test_focus_search(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    focuses.add("Astrophysics")
    focuses.add("Warp Field Dynamics")
    assert focuses.search("warp") == ["Warp Field Dynamics"]
    assert set(focuses.search("")) == {"Astrophysics", "Warp Field Dynamics"}


def test_focus_remove(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    focuses.add("Astrophysics")
    focuses.add("Diplomacy")
    focuses.remove("Astrophysics")
    assert focuses.all_focuses() == ["Diplomacy"]


def test_libraries_are_isolated_per_config_dir(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    talents.save("Bold")
    focuses.add("Astrophysics")
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "other" / "campaign.db"))
    db.init_db()
    assert talents.all_talents() == []
    assert focuses.all_focuses() == []
