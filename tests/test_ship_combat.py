import ship_combat as sc
import db


def test_add_ship_is_idempotent_and_records_side_and_power():
    state = sc.default_ship_combat()
    state = sc.add_ship(state, 1, sc.CREW, power_max=9)
    state = sc.add_ship(state, 1, sc.CREW, power_max=9)  # duplicate
    assert [s["entity_id"] for s in state["ships"]] == [1]
    assert state["ships"][0]["side"] == sc.CREW
    assert state["ships"][0]["power_max"] == 9


def test_start_conflict_crew_first_and_fills_power():
    state = sc.default_ship_combat()
    state = sc.add_ship(state, 1, sc.ADVERSARY, power_max=8)
    state = sc.add_ship(state, 2, sc.CREW, power_max=10)
    state = sc.start_conflict(state)
    assert state["started"] is True
    assert sc.current_ship(state)["entity_id"] == 2   # crew act first
    assert all(s["power"] == s["power_max"] for s in state["ships"])


def test_turns_alternate_between_sides():
    state = sc.default_ship_combat()
    state = sc.add_ship(state, 1, sc.CREW, power_max=6)
    state = sc.add_ship(state, 2, sc.CREW, power_max=6)
    state = sc.add_ship(state, 3, sc.ADVERSARY, power_max=6)
    state = sc.start_conflict(state)
    assert sc.current_ship(state)["entity_id"] == 1
    state = sc.next_turn(state)
    assert sc.current_ship(state)["entity_id"] == 3   # opposite side
    state = sc.next_turn(state)
    assert sc.current_ship(state)["entity_id"] == 2   # remaining crew


def test_power_spends_and_refills_each_round():
    state = sc.default_ship_combat()
    state = sc.add_ship(state, 1, sc.CREW, power_max=8)
    state = sc.start_conflict(state)
    state["ships"][0]["power"] = sc.spend_power(state["ships"][0]["power"], 3)
    assert state["ships"][0]["power"] == 5
    state = sc.next_round(state)
    assert state["ships"][0]["power"] == 8   # refilled


def test_apply_ship_damage_returns_overflow_past_shields():
    assert sc.apply_ship_damage(10, 4) == (6, 0)
    assert sc.apply_ship_damage(10, 10) == (0, 0)
    assert sc.apply_ship_damage(10, 13) == (0, 3)   # 3 overflow -> becomes Breaches


def test_breaches_accumulate_per_system():
    state = sc.default_ship_combat()
    state = sc.add_ship(state, 1, sc.CREW, power_max=8)
    state = sc.add_breach(state, 1, "engines", 2)
    state = sc.add_breach(state, 1, "engines", 1)
    state = sc.add_breach(state, 1, "weapons", 1)
    ship = state["ships"][0]
    assert ship["breaches"]["engines"] == 3
    assert sc.total_breaches(ship) == 4


def test_set_range_only_accepts_known_bands():
    state = sc.set_range(sc.default_ship_combat(), "Close")
    assert state["range"] == "Close"
    state = sc.set_range(state, "Warp 9")   # bogus -> unchanged
    assert state["range"] == "Close"


def test_traits_add_remove_and_tick():
    state = sc.default_ship_combat()
    state = sc.add_ship(state, 1, sc.CREW, power_max=8)
    state = sc.add_trait(state, 1, "Hull Breach", 1)
    state = sc.add_trait(state, 1, "Cloaked", None)
    state = sc.start_conflict(state)
    state = sc.next_turn(state)   # sole ship acts -> new round, tick
    names = [t["name"] for t in state["ships"][0]["traits"]]
    assert names == ["Cloaked"]   # the 1-round trait expired


def test_remove_ship_clears_current_and_stops_when_empty():
    state = sc.default_ship_combat()
    state = sc.add_ship(state, 1, sc.CREW, power_max=8)
    state = sc.start_conflict(state)
    state = sc.remove_ship(state, 1)
    assert state["ships"] == []
    assert state["started"] is False
    assert state["current_ship_id"] is None


def test_normalize_fills_defaults():
    assert sc.normalize_ship_combat(None) == sc.default_ship_combat()
    partial = sc.normalize_ship_combat({"ships": [{"entity_id": "7"}]})
    assert partial["ships"][0] == {
        "entity_id": 7, "side": sc.ADVERSARY, "has_acted": False,
        "power": 0, "power_max": 0, "breaches": {}, "traits": [],
    }


def test_db_persists_ship_combat_field(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    ship_id = db.create_entity("starship", "USS Reliant", {}, "")
    enc_id = db.create_entity("encounter", "Battle of Wolf 359", {}, "")
    state = sc.add_ship(sc.default_ship_combat(), ship_id, sc.CREW, power_max=10)
    db.update_entity(enc_id, "Battle of Wolf 359", {"ship_combat": state}, "")
    restored = db.get_entity(enc_id)["fields"]["ship_combat"]
    assert restored["ships"][0]["entity_id"] == ship_id
    assert restored["ships"][0]["power_max"] == 10


def test_db_rejects_malformed_ship_combat(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    import pytest
    with pytest.raises(ValueError, match="ship_combat'\\] must be an object"):
        db.create_entity("encounter", "Bad", {"ship_combat": "nope"}, "")
