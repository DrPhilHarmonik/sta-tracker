"""Regression test: EntityFormScreen.action_save() only collects the flat
schema fields (race, level, etc.), never sheet/active_effects/combat. Saving
an edit used to pass that incomplete dict straight to db.update_entity(),
which replaces the fields column wholesale -- silently wiping a character's
sheet, active effects, and combat data just from opening Edit and clicking
Save with no changes at all."""
import asyncio

import db
from app import STAApp


def run(scenario):
    asyncio.run(scenario())


def test_editing_flat_fields_preserves_sheet(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    adv_id = db.create_entity("adventurer", "Test Hero", {"species": "Human", "rank": "Ensign"}, "")
    db.update_entity(adv_id, "Test Hero", {
        "species": "Human", "rank": "Ensign",
        "sheet": {
            "attributes": {"control": 11, "daring": 10, "fitness": 10, "insight": 9, "presence": 9, "reason": 8},
            "departments": {"command": 3, "conn": 2, "engineering": 1, "security": 2, "medicine": 1, "science": 1},
            "focuses": ["Astrophysics"],
        },
    }, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            detail = app.screen
            detail.action_edit()
            await pilot.pause()
            form = app.screen
            # change one flat field, like a GM correcting a typo
            form.query_one("#field-rank").value = "Lieutenant"
            form.action_save()
            await pilot.pause()

        fields = db.get_entity(adv_id)["fields"]
        assert fields["rank"] == "Lieutenant"
        assert fields["sheet"]["attributes"]["control"] == 11
        assert fields["sheet"]["focuses"] == ["Astrophysics"]

    run(scenario)


def test_saving_character_sheet_persists_sta_attributes(monkeypatch, tmp_path):
    """Editing an Attribute on the STA character sheet and saving persists an
    STA-shaped sheet (attributes/departments), routed through the DB's
    shape-aware normalization."""
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()
    adv_id = db.create_entity("adventurer", "Test Hero", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            detail = app.screen
            detail.action_open_sheet()
            for _ in range(8):
                await pilot.pause()
            sheet_screen = app.screen
            sheet_screen.query_one("#sta-attr-control").value = "11"
            sheet_screen.query_one("#sta-dept-science").value = "4"
            sheet_screen.action_save()
            await pilot.pause()

        sheet = db.get_entity(adv_id)["fields"]["sheet"]
        assert "attributes" in sheet
        assert sheet["attributes"]["control"] == 11
        assert sheet["departments"]["science"] == 4

    run(scenario)
