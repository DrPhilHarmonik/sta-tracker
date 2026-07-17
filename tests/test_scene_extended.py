import db
import extended
import scene


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


# -- extended tasks -----------------------------------------------------------

def test_extended_ships_empty(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert extended.all_tasks() == []
    assert extended.find("Repair") is None


def test_effective_difficulty_adds_resistance():
    task = extended.normalize({"name": "X", "difficulty": 2, "resistance": 3})
    assert extended.effective_difficulty(task) == 5


def test_save_and_find_and_completion(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    extended.save({"name": "Repair Warp Core", "work_total": 8, "magnitude": 2, "difficulty": 2, "resistance": 1})
    task = extended.find("repair warp core")
    assert task is not None
    assert task["work_total"] == 8
    assert not extended.is_complete(task)


def test_add_work_progresses_and_caps_at_total(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    extended.save({"name": "Decrypt", "work_total": 5})
    extended.add_work("Decrypt", 3)
    assert extended.find("Decrypt")["work_done"] == 3
    extended.add_work("Decrypt", 10)   # over-shoot caps
    task = extended.find("Decrypt")
    assert task["work_done"] == 5
    assert extended.is_complete(task)


def test_add_work_unknown_task_returns_none(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert extended.add_work("Nope", 1) is None


def test_save_upserts_by_name(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    extended.save({"name": "Repair", "work_total": 5})
    extended.save({"name": "repair", "work_total": 9})
    assert len(extended.all_tasks()) == 1
    assert extended.find("Repair")["work_total"] == 9


def test_remove_task(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    extended.save({"name": "A"})
    extended.save({"name": "B"})
    extended.remove("A")
    assert [t["name"] for t in extended.all_tasks()] == ["B"]


# -- directives & scene traits ------------------------------------------------

def test_scene_starts_empty(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert scene.directives() == []
    assert scene.traits() == []


def test_directives_add_remove_and_dedupe(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    scene.add_directive("Investigate, do not engage")
    scene.add_directive("investigate, do not engage")  # dupe
    scene.add_directive("  ")
    assert scene.directives() == ["Investigate, do not engage"]
    scene.remove_directive("Investigate, do not engage")
    assert scene.directives() == []


def test_scene_traits_add_remove(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    scene.add_trait("Ion Storm")
    scene.add_trait("Zero Gravity")
    assert set(scene.traits()) == {"Ion Storm", "Zero Gravity"}
    scene.remove_trait("Ion Storm")
    assert scene.traits() == ["Zero Gravity"]


def test_directives_and_traits_are_independent(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    scene.add_directive("The Prime Directive applies")
    scene.add_trait("Nebula")
    assert scene.directives() == ["The Prime Directive applies"]
    assert scene.traits() == ["Nebula"]


def test_scene_isolated_per_config_dir(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    scene.add_directive("Explore")
    extended.save({"name": "Repair"})
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "other" / "campaign.db"))
    db.init_db()
    assert scene.directives() == []
    assert extended.all_tasks() == []
