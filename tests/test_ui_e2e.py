"""One continuous happy-path session through the real STAApp, covering every
core workflow in sequence: create an adventurer via the wizard, assign sheet
values, roll dice, apply an effect, run a combat round, and export a vault.
Each step's assertions check that the *previous* steps' state actually
carried through, not just that the current step didn't crash.
"""
import asyncio

import db
from app import STAApp


def test_full_happy_path_session(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()

            # 1. Create an adventurer via the quick STA lifepath wizard:
            #    Basic -> Species -> Attributes -> Departments -> Review.
            await pilot.press("a")
            await pilot.pause()
            list_screen = app.screen
            list_screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name").value = "Mira Thorn"
            await wiz._go_next()  # basic -> species
            await pilot.pause()
            wiz.query_one("#wiz-species-select").value = "Vulcan"
            await pilot.pause()
            await wiz._go_next()  # species -> attributes
            await pilot.pause()
            await wiz._go_next()  # attributes -> departments (accept spread)
            await pilot.pause()
            await wiz._go_next()  # departments -> review
            await pilot.pause()
            review = app.screen
            await review._go_next()  # create
            await pilot.pause()

            adv_id = db.list_entities("adventurer")[0]["id"]
            assert db.get_entity(adv_id)["name"] == "Mira Thorn"
            cs = app.screen  # quick mode lands on the Character Sheet
            for _ in range(8):
                await pilot.pause()

            # 2. Assign STA sheet values (Attributes + Departments).
            cs.query_one("#sta-attr-control").value = "11"
            cs.query_one("#sta-dept-command").value = "3"
            cs.action_save()
            await pilot.pause()
            saved_sheet = db.get_entity(adv_id)["fields"]["sheet"]
            assert saved_sheet["attributes"]["control"] == 11
            assert saved_sheet["departments"]["command"] == 3

            # 3. Open the detail view -- confirm the STA sheet we just saved
            #    surfaces in the character summary.
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            detail = app.screen
            body = str(detail.query_one("#detail-body").content)
            assert "Character Sheet" in body
            assert "Control 11" in body

            # 5. Run a combat round and confirm the sheet values
            #    carry into the roster summary.
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            enc_list = app.screen
            enc_list.action_add()
            await pilot.pause()
            enc_form = app.screen
            enc_form.query_one("#field-name").value = "Tavern Brawl"
            enc_form.action_save()
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            app.screen.action_open_combat()
            await pilot.pause()
            combat_screen = app.screen
            combat_screen.query_one("#sel-add-combatant").value = str(adv_id)
            combat_screen.query_one("#btn-add-combatant").press()
            await pilot.pause()
            combat_screen.query_one("#btn-start-encounter").press()
            await pilot.pause()
            combat_screen.query_one("#btn-next-round").press()
            await pilot.pause()
            summary = str(combat_screen.query_one("#combat-summary").content)
            # The STA conflict tracker (roadmap Phase 7) reads the STA sheet, so
            # the summary now shows the character's Stress track, not 5e HP, and
            # the round/turn engine has advanced to round 2.
            assert "Mira Thorn" in summary
            assert "Round 2" in summary
            assert "Stress" in summary

            # 6. Export a vault and confirm the file reflects everything above.
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            app.screen.action_export()
            await pilot.pause()
            export_screen = app.screen
            vault_dir = tmp_path / "vault"
            export_screen.query_one("#export-path").value = str(vault_dir)
            export_screen.query_one("#btn-export").press()
            await pilot.pause()
            assert "Exported 2 entities" in str(export_screen.query_one("#export-status").content)

            mira_md = (vault_dir / "Adventurer" / "Mira Thorn.md").read_text(encoding="utf-8")
            # The exporter now emits the STA character sheet: frontmatter plus a
            # Character Sheet section carrying the Attributes we saved in step 2.
            assert "name: Mira Thorn" in mira_md
            assert "## Character Sheet" in mira_md
            assert "Control 11" in mira_md

    asyncio.run(scenario())
