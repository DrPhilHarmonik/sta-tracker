"""What `ctrl+p` offers: every screen, and every entity by name.

Textual installs a command palette in every app and this one answered it with a
single entry -- its own name -- while carrying 24 screens and a campaign full of
named people, ships and places. The provider below fills it in.

Two kinds of hit:

* **Go to ...** -- the dashboard's destinations, so the palette reaches them
  without remembering which letter opens Adversaries.
* **The entities themselves** -- every NPC, ship, quest and session by name,
  opening its detail screen. This is the half a keyboard shortcut cannot do,
  because the names are the campaign's, not the app's.

Matching is Textual's own matcher rather than anything invented here: it is what
ranks the palette everywhere else, and a second scheme would only disagree with
it.
"""

from __future__ import annotations

from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

import db
from models import ENTITY_LABELS

# Dashboard destinations, as (title, the Dashboard action that opens it).
# Actions rather than screen classes: the dashboard already knows how to build
# each screen with the right arguments, and duplicating that here is how the two
# routes drift apart.
NAVIGATION = [
    ("Party Overview", "party_overview"),
    ("Adversaries", "monster_ref"),
    ("Talents & Focuses", "reference"),
    ("Scene & Directives", "scene"),
    ("Timeline", "timeline"),
    ("Relationships", "relationship_browser"),
    ("Campaigns", "campaigns"),
    ("Backup & Restore", "backup"),
    ("Export to Markdown", "export"),
    ("Search All", "search"),
]


class STACommands(Provider):
    """Campaign navigation and entity lookup for the command palette."""

    async def startup(self) -> None:
        # Read once per palette opening rather than per keystroke: `search` is
        # called on every character typed, and a campaign is a database query.
        self._entities = [
            (entity["id"], entity["name"], ENTITY_LABELS.get(entity["type"], entity["type"]))
            for entity in db.list_entities()
        ]

    def _go(self, action: str) -> None:
        """Run a Dashboard action, from wherever the palette was opened.

        The dashboard is the bottom of the stack, so its actions are reachable
        even when the palette was opened three screens deep -- which is the
        point of a palette.
        """
        from screens.dashboard import Dashboard

        for screen in self.app.screen_stack:
            if isinstance(screen, Dashboard):
                getattr(screen, f"action_{action}")()
                return

    def _open_entity(self, entity_id: int) -> None:
        from screens.entities import EntityDetailScreen

        self.app.push_screen(EntityDetailScreen(entity_id))

    async def discover(self) -> Hits:
        """What the palette shows before anything is typed: the destinations.

        Not the entities -- a campaign has hundreds and the discovery list is a
        menu, not a dump.
        """
        for title, action in NAVIGATION:
            yield DiscoveryHit(f"Go to {title}", partial(self._go, action))

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)

        for title, action in NAVIGATION:
            label = f"Go to {title}"
            score = matcher.match(label)
            if score > 0:
                yield Hit(score, matcher.highlight(label), partial(self._go, action))

        for entity_id, name, type_label in self._entities:
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(name),
                    partial(self._open_entity, entity_id),
                    help=type_label,
                )
