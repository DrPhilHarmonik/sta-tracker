import asyncio

from textual.color import Color

import db
import settings
from app import STAApp


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    monkeypatch.setenv("STA_SETTINGS_PATH", str(tmp_path / "settings.json"))
    db.init_db()


def test_app_boots_on_sta_dark_by_default(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            assert app.theme == "sta-dark"

    run(scenario)


def test_stylesheet_variables_resolve_to_original_colors(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            resolved = app.get_css_variables()
            # A no-op default: the variables the stylesheet now references still
            # resolve to the exact hexes that used to be hardcoded.
            assert Color.parse(resolved["sta-bg"]) == Color.parse("#1a1a2e")
            assert Color.parse(resolved["sta-panel"]) == Color.parse("#16213e")
            assert Color.parse(resolved["sta-accent"]) == Color.parse("#c792ea")
            assert Color.parse(resolved["sta-entity-enemy"]) == Color.parse("#ff5370")

    run(scenario)


def test_cycle_theme_flips_and_persists(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            assert app.theme == "sta-dark"
            app.action_cycle_theme()
            await pilot.pause()
            assert app.theme == "sta-light"
            # persisted to the settings file
            assert settings.get_setting("theme") == "sta-light"

    run(scenario)


def test_saved_theme_is_restored_on_next_launch(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    settings.set_setting("theme", "sta-light")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            assert app.theme == "sta-light"

    run(scenario)


def test_toggle_via_keybinding(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+t")
            await pilot.pause()
            assert app.theme == "sta-light"
            assert settings.get_setting("theme") == "sta-light"

    run(scenario)


def test_unknown_saved_theme_falls_back_to_default(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    settings.set_setting("theme", "bogus-theme")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            assert app.theme == "sta-dark"

    run(scenario)
