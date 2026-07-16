import db
import momentum


# -- momentum rules -----------------------------------------------------------

def test_clamp_momentum_bounds():
    assert momentum.clamp_momentum(-3) == 0
    assert momentum.clamp_momentum(0) == 0
    assert momentum.clamp_momentum(6) == 6
    assert momentum.clamp_momentum(9) == momentum.MOMENTUM_MAX == 6


def test_clamp_threat_has_no_ceiling():
    assert momentum.clamp_threat(-2) == 0
    assert momentum.clamp_threat(0) == 0
    assert momentum.clamp_threat(25) == 25


def test_seed_threat_is_twice_the_players():
    assert momentum.seed_threat(4) == 8
    assert momentum.seed_threat(0) == 0
    assert momentum.seed_threat(-1) == 0


# -- campaign-state persistence -----------------------------------------------

def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def test_get_pools_defaults_to_zero(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert db.get_pools() == {"momentum": 0, "threat": 0}


def test_set_and_adjust_pools(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.set_pools(3, 5)
    assert db.get_pools() == {"momentum": 3, "threat": 5}

    assert db.adjust_momentum(2) == {"momentum": 5, "threat": 5}
    assert db.adjust_threat(-1) == {"momentum": 5, "threat": 4}


def test_pools_clamp_on_write(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.set_pools(99, 99)
    assert db.get_pools() == {"momentum": 6, "threat": 99}

    db.adjust_momentum(-100)
    db.adjust_threat(-100)
    assert db.get_pools() == {"momentum": 0, "threat": 0}


def test_pools_persist_as_a_singleton_row(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.adjust_momentum(1)
    db.adjust_momentum(1)
    db.adjust_threat(3)
    # A second init_db() must not reset or duplicate the row.
    db.init_db()
    assert db.get_pools() == {"momentum": 2, "threat": 3}


def test_seed_threat_uses_active_adventurer_count(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.create_entity("adventurer", "Kira", {}, "")
    db.create_entity("adventurer", "Bashir", {}, "")
    db.create_entity("adventurer", "Retired One", {"status": "Retired"}, "")
    pools = db.seed_threat()
    assert pools["threat"] == 4  # two active adventurers x2

    assert db.seed_threat(5)["threat"] == 10


def test_reset_db_clears_pools(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.set_pools(4, 6)
    db.reset_db()
    assert db.get_pools() == {"momentum": 0, "threat": 0}
