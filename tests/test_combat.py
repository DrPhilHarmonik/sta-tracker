import combat


def test_add_combatant_is_idempotent():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.CREW)
    state = combat.add_combatant(state, 1, combat.CREW)
    assert [c["entity_id"] for c in state["combatants"]] == [1]


def test_add_combatant_records_side():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.CREW)
    state = combat.add_combatant(state, 2, combat.ADVERSARY)
    by_id = {c["entity_id"]: c["side"] for c in state["combatants"]}
    assert by_id == {1: combat.CREW, 2: combat.ADVERSARY}


def test_unknown_side_defaults_to_adversary():
    state = combat.add_combatant(combat.default_combat(), 1, "bogus")
    assert state["combatants"][0]["side"] == combat.ADVERSARY


def test_remove_combatant_resets_when_empty():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.CREW)
    state = combat.start_conflict(state)
    state = combat.remove_combatant(state, 1)
    assert state["combatants"] == []
    assert state["started"] is False
    assert state["current_entity_id"] is None


def test_start_conflict_puts_crew_first_no_initiative_sort():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.ADVERSARY)
    state = combat.add_combatant(state, 2, combat.CREW)
    state = combat.start_conflict(state)
    # Insertion order is preserved (no sort); the first turn goes to the crew.
    assert [c["entity_id"] for c in state["combatants"]] == [1, 2]
    assert state["started"] is True
    assert state["round"] == 1
    assert combat.current_combatant(state)["entity_id"] == 2
    assert state["active_side"] == combat.CREW


def test_turns_alternate_between_sides():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.CREW)
    state = combat.add_combatant(state, 2, combat.CREW)
    state = combat.add_combatant(state, 3, combat.ADVERSARY)
    state = combat.start_conflict(state)
    assert combat.current_combatant(state)["entity_id"] == 1  # crew
    state = combat.next_turn(state)
    assert combat.current_combatant(state)["entity_id"] == 3  # adversary
    state = combat.next_turn(state)
    assert combat.current_combatant(state)["entity_id"] == 2  # back to remaining crew
    assert state["round"] == 1


def test_next_turn_starts_new_round_when_all_acted():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.CREW)
    state = combat.add_combatant(state, 2, combat.ADVERSARY)
    state = combat.start_conflict(state)
    state = combat.next_turn(state)  # -> adversary
    state = combat.next_turn(state)  # everyone acted -> round 2, crew first
    assert state["round"] == 2
    assert combat.current_combatant(state)["entity_id"] == 1
    assert all(not c["has_acted"] for c in state["combatants"])


def test_next_round_skips_remaining_turns_and_ticks_conditions():
    state = combat.default_combat()
    for entity_id in (1, 2, 3):
        state = combat.add_combatant(state, entity_id, combat.CREW)
    state = combat.add_condition(state, 1, "Dazed", 1)
    state = combat.start_conflict(state)
    state = combat.next_round(state)
    assert state["round"] == 2
    assert combat.current_combatant(state)["entity_id"] == 1
    assert state["combatants"][0]["conditions"] == []


def test_round_wrap_ticks_and_expires_conditions_but_keeps_indefinite():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.CREW)
    state = combat.add_condition(state, 1, "Dazed", 1)
    state = combat.add_condition(state, 1, "Injured", None)
    state = combat.start_conflict(state)
    state = combat.next_turn(state)  # sole combatant acted -> new round, tick
    names = [c["name"] for c in state["combatants"][0]["conditions"]]
    assert names == ["Injured"]


def test_current_combatant_none_when_empty():
    assert combat.current_combatant(combat.default_combat()) is None


def test_add_and_remove_condition():
    state = combat.default_combat()
    state = combat.add_combatant(state, 1, combat.CREW)
    state = combat.add_condition(state, 1, "Prone", None)
    state = combat.add_condition(state, 1, "Dazed", 2)
    assert len(state["combatants"][0]["conditions"]) == 2
    state = combat.remove_condition(state, 1, 0)
    assert [c["name"] for c in state["combatants"][0]["conditions"]] == ["Dazed"]


def test_apply_stress_floors_at_zero():
    assert combat.apply_stress(10, 15) == 0
    assert combat.apply_stress(10, 4) == 6


def test_recover_stress_caps_at_max():
    assert combat.recover_stress(10, 20, 5) == 15
    assert combat.recover_stress(18, 20, 50) == 20


def test_normalize_combat_fills_defaults_for_missing_data():
    normalized = combat.normalize_combat(None)
    assert normalized == combat.default_combat()

    partial = combat.normalize_combat({"combatants": [{"entity_id": "7"}]})
    assert partial["combatants"] == [
        {"entity_id": 7, "side": combat.ADVERSARY, "has_acted": False, "conditions": []}
    ]
