"""UI interaction tests for the STA wizard's Species step: it seeds an
Adventurer's Attribute spread with the species' bonuses, the Human choose-3
sub-step appears and validates distinct picks, and the whole lifepath flow
produces an STA-shaped sheet."""
import asyncio

import db
import species
from app import STAApp
from textual.widgets import Input, Select


def run(scenario):
    asyncio.run(scenario())


async def _open_adventurer_wizard(app, pilot, mode="quick"):
    await pilot.press("a")
    await pilot.pause()
    app.screen.action_wizard(mode)
    await pilot.pause()
    return app.screen


def test_species_step_present_and_seeds_fixed_bonuses(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wiz = await _open_adventurer_wizard(app, pilot)
            assert "species" in wiz.steps

            wiz.query_one("#wiz-name", Input).value = "Sotek"
            await wiz._go_next()  # basic -> species
            await pilot.pause()
            wiz.query_one("#wiz-species-select", Select).value = "Vulcan"
            await pilot.pause()
            await wiz._go_next()  # species -> attributes
            await pilot.pause()
            await wiz._go_next()  # attributes -> departments (accept spread)
            await pilot.pause()
            await wiz._go_next()  # departments -> review
            await pilot.pause()
            await wiz._go_next()  # create
            for _ in range(6):
                await pilot.pause()

        adv = db.list_entities("adventurer")[0]
        sheet = db.get_entity(adv["id"])["fields"]["sheet"]
        assert "attributes" in sheet  # STA-shaped
        assert sheet["species"] == "Vulcan"
        # Vulcan grants +1 Control/Fitness/Reason on top of the base spread.
        from screens.wizard import DEFAULT_ATTRIBUTE_SPREAD as base
        assert sheet["attributes"]["control"] == base["control"] + 1
        assert sheet["attributes"]["fitness"] == base["fitness"] + 1
        assert sheet["attributes"]["reason"] == base["reason"] + 1
        # Un-bonused Attribute is unchanged.
        assert sheet["attributes"]["daring"] == base["daring"]

    run(scenario)


def test_human_choice_bonus_applies_to_picked_attributes(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wiz = await _open_adventurer_wizard(app, pilot)
            wiz.query_one("#wiz-name", Input).value = "Ada Vance"
            await wiz._go_next()  # basic -> species
            await pilot.pause()
            # Human is the default; the three choice pickers should exist.
            assert wiz.query_one("#wiz-species-select", Select).value == "Human"
            wiz.query_one("#wiz-species-choice-0", Select).value = "daring"
            wiz.query_one("#wiz-species-choice-1", Select).value = "insight"
            wiz.query_one("#wiz-species-choice-2", Select).value = "reason"
            await wiz._go_next()  # species -> attributes
            await pilot.pause()
            await wiz._go_next()  # attributes -> departments
            await pilot.pause()
            await wiz._go_next()  # departments -> review
            await pilot.pause()
            await wiz._go_next()  # create
            for _ in range(6):
                await pilot.pause()

        adv = db.list_entities("adventurer")[0]
        sheet = db.get_entity(adv["id"])["fields"]["sheet"]
        from screens.wizard import DEFAULT_ATTRIBUTE_SPREAD as base
        assert sheet["attributes"]["daring"] == base["daring"] + 1
        assert sheet["attributes"]["insight"] == base["insight"] + 1
        assert sheet["attributes"]["reason"] == base["reason"] + 1
        assert sheet["attributes"]["control"] == base["control"]

    run(scenario)


def test_human_duplicate_choice_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wiz = await _open_adventurer_wizard(app, pilot)
            wiz.query_one("#wiz-name", Input).value = "Ada Vance"
            await wiz._go_next()  # basic -> species
            await pilot.pause()
            wiz.query_one("#wiz-species-choice-0", Select).value = "daring"
            wiz.query_one("#wiz-species-choice-1", Select).value = "daring"
            wiz.query_one("#wiz-species-choice-2", Select).value = "reason"
            await wiz._go_next()  # rejected -> stays on species
            await pilot.pause()
            assert wiz.steps[wiz.step_index] == "species"
            assert "different" in str(wiz.query_one("#wizard-error").content).lower()

    run(scenario)


def test_advanced_mode_captures_focuses_values_and_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wiz = await _open_adventurer_wizard(app, pilot, mode="advanced")
            assert "focuses_values" in wiz.steps
            assert "talents_profile" in wiz.steps

            wiz.query_one("#wiz-name", Input).value = "Jael Rix"
            await wiz._go_next()  # basic -> species
            await pilot.pause()
            wiz.query_one("#wiz-species-select", Select).value = "Bajoran"
            await pilot.pause()
            await wiz._go_next()  # species -> attributes
            await pilot.pause()
            await wiz._go_next()  # attributes -> departments
            await pilot.pause()
            await wiz._go_next()  # departments -> focuses_values
            await pilot.pause()
            wiz.query_one("#wiz-focus-input", Input).value = "Astrophysics"
            wiz.query_one("#btn-wiz-add-focus").press()
            await pilot.pause()
            wiz.query_one("#wiz-value-input", Input).value = "The needs of the many"
            wiz.query_one("#btn-wiz-add-value").press()
            await pilot.pause()
            await wiz._go_next()  # focuses_values -> talents_profile
            await pilot.pause()
            wiz.query_one("#wiz-talent-input", Input).value = "Bold: Command"
            wiz.query_one("#btn-wiz-add-talent").press()
            await pilot.pause()
            wiz.query_one("#wiz-rank", Input).value = "Lieutenant"
            wiz.query_one("#wiz-career", Input).value = "Officer"
            wiz.query_one("#wiz-role", Input).value = "Science Officer"
            await wiz._go_next()  # talents_profile -> review
            await pilot.pause()
            wiz.query_one("#wiz-determination", Input).value = "2"
            await wiz._go_next()  # create
            for _ in range(6):
                await pilot.pause()

        adv = db.list_entities("adventurer")[0]
        entity = db.get_entity(adv["id"])
        sheet = entity["fields"]["sheet"]
        assert sheet["focuses"] == ["Astrophysics"]
        assert sheet["values"] == ["The needs of the many"]
        assert sheet["talents"] == ["Bold: Command"]
        assert sheet["rank"] == "Lieutenant"
        assert sheet["career"] == "Officer"
        assert sheet["role"] == "Science Officer"
        assert sheet["determination"] == 2
        # Thin compat flat fields for the list views.
        assert entity["fields"]["race"] == "Bajoran"
        assert entity["fields"]["class_name"] == "Officer"

    run(scenario)


def test_attribute_out_of_range_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            wiz = await _open_adventurer_wizard(app, pilot)
            wiz.query_one("#wiz-name", Input).value = "Sotek"
            await wiz._go_next()  # basic -> species
            await pilot.pause()
            await wiz._go_next()  # species -> attributes
            await pilot.pause()
            wiz.query_one("#wiz-attr-control", Input).value = "40"
            await wiz._go_next()  # rejected -> stays on attributes
            await pilot.pause()
            assert wiz.steps[wiz.step_index] == "attributes"

    run(scenario)
