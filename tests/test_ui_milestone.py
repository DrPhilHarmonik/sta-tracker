import asyncio

import db
from app import STAApp
from screens.milestone import MilestoneScreen
from screens.entities import EntityDetailScreen
from textual.widgets import Select, Input


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()


def _make_pc():
    eid = db.create_entity("adventurer", "Sotek", {}, "")
    db.update_entity(eid, "Sotek", {
        "sheet": {
            "attributes": {"control": 10, "daring": 9, "fitness": 10, "insight": 9, "presence": 8, "reason": 11},
            "departments": {"command": 3, "conn": 2, "engineering": 1, "security": 2, "medicine": 1, "science": 2},
            "focuses": ["Logic"],
        },
    }, "")
    return eid


async def _open_milestones(pilot, app, eid):
    app.push_screen(MilestoneScreen(eid))
    for _ in range(6):
        await pilot.pause()
    return app.screen


def test_swap_attributes_milestone_applies_and_logs(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            screen.query_one("#milestone-op", Select).value = "swap_attr"
            screen.query_one("#milestone-attr-up", Select).value = "control"    # 10 -> 11
            screen.query_one("#milestone-attr-down", Select).value = "daring"   # 9 -> 8
            screen.query_one("#milestone-type", Select).value = "Spotlight"
            screen.query_one("#btn-apply-milestone").press()
            await pilot.pause()

        sheet = db.get_entity(eid)["fields"]["sheet"]
        assert sheet["attributes"]["control"] == 11
        assert sheet["attributes"]["daring"] == 8
        assert len(sheet["milestones"]) == 1
        assert sheet["milestones"][0]["type"] == "Spotlight"
        assert "Control +1" in sheet["milestones"][0]["note"]
        assert sheet["milestones"][0]["date"]  # a date was stamped

    run(scenario)


def test_illegal_swap_is_refused_without_changing_the_sheet(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()  # reason is 11; try to push it past 12 by swapping onto it twice

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            screen.query_one("#milestone-op", Select).value = "increase_attr"
            screen.query_one("#milestone-attr-up", Select).value = "reason"  # 11 -> 12 (ok)
            screen.query_one("#btn-apply-milestone").press()
            await pilot.pause()
            # Second increase would exceed the ceiling -> refused.
            screen.query_one("#btn-apply-milestone").press()
            await pilot.pause()
            assert "maximum" in str(screen.query_one("#milestone-status").content).lower()

        sheet = db.get_entity(eid)["fields"]["sheet"]
        assert sheet["attributes"]["reason"] == 12          # first one applied
        assert len(sheet["milestones"]) == 1                # second one didn't log

    run(scenario)


def test_add_focus_milestone_adds_focus_and_remembers_it(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            screen.query_one("#milestone-op", Select).value = "add_focus"
            screen.query_one("#milestone-focus", Input).value = "Warp Field Dynamics"
            screen.query_one("#btn-apply-milestone").press()
            await pilot.pause()

        import focuses
        sheet = db.get_entity(eid)["fields"]["sheet"]
        assert "Warp Field Dynamics" in sheet["focuses"]
        assert "Warp Field Dynamics" in focuses.all_focuses()

    run(scenario)


def test_note_only_requires_a_note(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            screen.query_one("#milestone-op", Select).value = "note_only"
            screen.query_one("#btn-apply-milestone").press()
            await pilot.pause()
            assert "note" in str(screen.query_one("#milestone-status").content).lower()
        assert db.get_entity(eid)["fields"]["sheet"]["milestones"] == []

    run(scenario)


def test_end_of_mission_updates_reputation_and_reprimands(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            screen.query_one("#reputation-delta", Input).value = "2"
            screen.query_one("#reprimand-delta", Input).value = "1"
            screen.query_one("#btn-apply-reputation").press()
            await pilot.pause()
            # inputs reset after applying
            assert screen.query_one("#reputation-delta", Input).value == "0"

        sheet = db.get_entity(eid)["fields"]["sheet"]
        assert sheet["reputation"] == 3   # started at default 1, +2
        assert sheet["reprimands"] == 1

    run(scenario)


def test_propose_from_mission_fills_deltas_then_applies(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            # a successful mission with one reprimand: +1 base, -1 reprimand = 0 rep, +1 reprimand
            screen.query_one("#mission-outcome", Select).value = "succeeded"
            screen.query_one("#mission-reprimands", Input).value = "1"
            screen.query_one("#btn-propose-reputation").press()
            await pilot.pause()
            assert screen.query_one("#reputation-delta", Input).value == "0"
            assert screen.query_one("#reprimand-delta", Input).value == "1"
            # now a clean success proposes +1 and applies it
            screen.query_one("#mission-reprimands", Input).value = "0"
            screen.query_one("#btn-propose-reputation").press()
            await pilot.pause()
            assert screen.query_one("#reputation-delta", Input).value == "1"
            screen.query_one("#btn-apply-reputation").press()
            await pilot.pause()

        sheet = db.get_entity(eid)["fields"]["sheet"]
        assert sheet["reputation"] == 2   # default 1, +1
        assert sheet["reprimands"] == 0

    run(scenario)


def test_reputation_readout_shows_standing(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            readout = str(screen.query_one("#reputation-readout").content)
            assert "Untested" in readout   # default reputation 1

    run(scenario)


def test_end_of_mission_requires_a_nonzero_change(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            screen = await _open_milestones(pilot, app, eid)
            screen.query_one("#btn-apply-reputation").press()  # both deltas 0
            await pilot.pause()
            assert "change" in str(screen.query_one("#reputation-status").content).lower()

    run(scenario)


def test_milestones_button_only_shows_for_adventurers(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    eid = _make_pc()
    ship_id = db.create_entity("starship", "USS Reliant", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            app.push_screen(EntityDetailScreen(eid))
            for _ in range(6):
                await pilot.pause()
            assert app.screen.query_one("#btn-milestones") is not None
            app.pop_screen()
            for _ in range(4):
                await pilot.pause()
            app.push_screen(EntityDetailScreen(ship_id))
            for _ in range(6):
                await pilot.pause()
            assert len(app.screen.query("#btn-milestones")) == 0

    run(scenario)
