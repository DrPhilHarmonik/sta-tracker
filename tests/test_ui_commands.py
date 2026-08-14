"""The command palette provider (Phase 30).

Textual installs `ctrl+p` in every app; this one answered with a single entry
until now. These check both halves of what it should offer -- the app's screens,
and the campaign's own names.

The provider is driven directly rather than through the palette UI: Textual owns
the palette's input handling and ranking, and testing it would be testing the
framework.
"""
import asyncio

import db
from app import STAApp
from commands import NAVIGATION, STACommands


def run(scenario):
    asyncio.run(scenario())


def _setup(monkeypatch, tmp_path):
    monkeypatch.setenv("STA_DB_PATH", str(tmp_path / "campaign.db"))
    monkeypatch.setenv("STA_SETTINGS_PATH", str(tmp_path / "settings.json"))
    db.init_db()


async def _provider(app):
    provider = STACommands(app.screen)
    await provider.startup()
    return provider


async def _hits(provider, query):
    return [hit async for hit in provider.search(query)]


def test_the_provider_is_registered_with_the_app(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            assert STACommands in app.COMMANDS

    run(scenario)


def test_textuals_own_commands_are_kept(monkeypatch, tmp_path):
    """The palette should still offer the theme picker it offers everywhere."""
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            assert len(app.COMMANDS) > 1

    run(scenario)


def test_the_discovery_list_offers_the_destinations(monkeypatch, tmp_path):
    """What the palette shows before anything is typed."""
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            provider = await _provider(app)

            hits = [hit async for hit in provider.discover()]
            labels = {str(hit.prompt) for hit in hits}

            assert len(hits) == len(NAVIGATION)
            assert "Go to Timeline" in labels
            # Not the entities: a campaign has hundreds and this is a menu.
            assert not any("Sarek" in label for label in labels)

    run(scenario)


def test_searching_finds_a_destination(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            provider = await _provider(app)

            hits = await _hits(provider, "timeline")

            assert any("Timeline" in str(hit.prompt) for hit in hits)

    run(scenario)


def test_searching_finds_an_entity_by_name(monkeypatch, tmp_path):
    """The half a keyboard shortcut cannot do: the names are the campaign's."""
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")
    db.create_entity("starship", "USS Cerritos", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            provider = await _provider(app)

            hits = await _hits(provider, "cerritos")

            assert any("Cerritos" in str(hit.prompt) for hit in hits)

    run(scenario)


def test_an_entity_hit_says_what_kind_of_thing_it_is(monkeypatch, tmp_path):
    """Two entities can share a name; the type is how you tell them apart."""
    _setup(monkeypatch, tmp_path)
    db.create_entity("starship", "Defiant", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            provider = await _provider(app)

            hits = await _hits(provider, "defiant")

            assert hits and hits[0].help == "Starship"

    run(scenario)


def test_choosing_an_entity_opens_its_detail_screen(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    entity_id = db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            provider = await _provider(app)
            hits = await _hits(provider, "sarek")

            hits[0].command()
            await pilot.pause()

            from screens.entities import EntityDetailScreen
            assert isinstance(app.screen, EntityDetailScreen)
            assert app.screen.entity_id == entity_id

    run(scenario)


def test_choosing_a_destination_opens_it_from_a_deeper_screen(monkeypatch, tmp_path):
    """A palette that only works on the dashboard is not a palette."""
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            await pilot.press("n")           # two screens deep now
            await pilot.pause()
            provider = await _provider(app)

            hits = await _hits(provider, "timeline")
            next(h for h in hits if "Timeline" in str(h.prompt)).command()
            await pilot.pause()

            from screens.timeline import TimelineScreen
            assert isinstance(app.screen, TimelineScreen)

    run(scenario)


def test_a_query_matching_nothing_returns_nothing(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    db.create_entity("npc", "Sarek", {}, "")

    async def scenario():
        app = STAApp()
        async with app.run_test(size=(160, 50)) as pilot:
            await pilot.pause()
            provider = await _provider(app)

            assert await _hits(provider, "zzzzzzzz") == []

    run(scenario)
