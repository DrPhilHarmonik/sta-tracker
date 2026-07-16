import conditions as cnd


def test_condition_library_is_non_empty():
    assert len(cnd.CONDITIONS) >= 8


def test_condition_names_matches_keys():
    assert cnd.CONDITION_NAMES == list(cnd.CONDITIONS.keys())


def test_all_conditions_have_non_empty_description():
    for name, desc in cnd.CONDITIONS.items():
        assert desc.strip(), f"{name} has empty description"
        assert len(desc) > 10, f"{name} description too short"


def test_sta_relevant_traits_present():
    for name in ["Injured", "Blinded", "Restrained", "Exposed", "Cover"]:
        assert name in cnd.CONDITIONS, f"Missing trait: {name}"


def test_descriptions_reference_stress_or_tasks():
    # STA traits are framed around Tasks/Difficulty/Stress, not 5e mechanics.
    joined = " ".join(cnd.CONDITIONS.values()).lower()
    assert "task" in joined
    assert "stress" in joined
