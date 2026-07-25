import search
import db


def _char(name, sheet, notes=""):
    return {"type": "adventurer", "name": name, "notes": notes, "fields": {"sheet": sheet}}


def test_sheet_terms_flattens_character_content():
    entity = _char("Kira", {
        "species": "Bajoran", "rank": "Major", "role": "First Officer",
        "focuses": ["Astrophysics", "Warp Field Dynamics"],
        "values": ["The Prophets guide me"],
        "talents": ["Bold: Command"],
    })
    terms = dict(search.sheet_terms(entity))
    assert terms["Species"] == "Bajoran"
    assert terms["Rank"] == "Major"
    labels = [label for label, _ in search.sheet_terms(entity)]
    assert labels.count("Focus") == 2


def test_sheet_terms_uses_starship_shape_when_systems_present():
    ship = {"type": "starship", "name": "Defiant", "notes": "",
            "fields": {"sheet": {"systems": {}, "talents": ["Ablative Armor"], "traits": ["Federation Starship"]}}}
    terms = dict(search.sheet_terms(ship))
    assert terms["Talent"] == "Ablative Armor"
    assert terms["Trait"] == "Federation Starship"


def test_match_reports_where_the_hit_landed():
    entity = _char("Kira", {"focuses": ["Warp Field Dynamics"]}, notes="Holds a grudge.")
    assert search.match(entity, "kira") == "Name"
    assert search.match(entity, "grudge") == "Notes"
    assert search.match(entity, "warp field") == "Focus: Warp Field Dynamics"
    assert search.match(entity, "nowhere") is None
    assert search.match(entity, "  ") is None


def test_entity_with_no_sheet_matches_only_name_and_notes():
    entity = {"type": "location", "name": "Deep Space 9", "notes": "Cardassian station.", "fields": {}}
    assert search.match(entity, "deep space") == "Name"
    assert search.match(entity, "cardassian") == "Notes"
    assert search.sheet_terms(entity) == []


def test_search_all_finds_sheet_content_and_annotates_match(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    hit = db.create_entity("adventurer", "Data", {"sheet": {"focuses": ["Warp Field Dynamics"]}}, "")
    db.create_entity("adventurer", "Worf", {"sheet": {"focuses": ["Bat'leth"]}}, "")

    results = db.search_all("warp field")
    assert [e["id"] for e in results] == [hit]
    assert results[0]["match"] == "Focus: Warp Field Dynamics"


def test_list_entities_search_reaches_into_sheet(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    hit = db.create_entity("adventurer", "Geordi", {"sheet": {"talents": ["Innovation"]}}, "")
    db.create_entity("adventurer", "Beverly", {"sheet": {"talents": ["Quick Study"]}}, "")

    results = db.list_entities("adventurer", "innovation")
    assert [e["id"] for e in results] == [hit]
