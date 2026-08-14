# STA Tracker

A terminal campaign manager for **Star Trek Adventures 2e** GMs, built with
Textual and SQLite.

It began as a fork of a D&D 5e DM tracker; the migration to the 2d20 ruleset
finished long ago (`STA_FORK_ROADMAP.md`, Phases 1–10), and everything since has
been new capability for STA (`STA_ROADMAP.md`, Phases 11–31).

**No bundled content.** STA has no open SRD, so the tool ships rules *maths* and
empty libraries. Talents, adversaries and spaceframes are yours to enter, and
the libraries fill themselves in as you play.

## The campaign

- NPCs, adventurers, enemies, starships, locations, quests, factions, items,
  sessions and encounters, each with typed fields and freeform notes.
- Relationships between any two of them, creatable before the entity is saved.
- Global search across every name, note and sheet (`/`), and per-list filters.
- Multiple campaigns, switchable in place.
- A timeline of sessions, and a campaign log exported as one Markdown file.

## The rules

- **Character and ship sheets** — Attributes, Departments, Focuses, Values,
  Talents, weapons, Stress and Injuries; a guided creation wizard with species.
- **Task rolls** — 2d20 against Attribute + Department, Focus, bought dice,
  Complication range, Challenge Dice for damage. `ctrl+r` rolls one from
  anywhere.
- **Momentum and Threat** — a shared pool bar, extra successes banked, bought
  dice paid for, Complications feeding Threat, and Threat carried between
  missions or not.
- **Determination and Values** — invoke to spend, challenge to regain.
- **Conflict** — a side-alternating tracker for personal combat, and a separate
  one for ship combat with Power, Shields, Breaches and crew stations.
- **Extended Tasks**, mission **Directives** and scene **Traits** — and a rolled
  Complication can be named and kept as a scene Trait.
- **Milestones and advancement**, **Reputation** standings and reprimands,
  between-scenes **recovery**.
- Reference libraries for Talents, Focuses, adversaries and spaceframes.

## At the table

- `?` (or F1) lists the keys the current screen answers to.
- `ctrl+p` opens the command palette: any screen, or any entity by name.
- `ctrl+n` captures a note mid-scene without leaving what you are doing.
- `ctrl+t` cycles the theme — dark, light, and an LCARS-flavoured one.
- One-page printable play aids for the characters and ships in play.

## Getting it out again

- Export to Markdown for an Obsidian vault, and import that vault back.
- A JSON backup that carries the whole campaign, including the pools and every
  library (see below).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 sta.py
```

By default, campaign data is stored at:

```text
~/.config/sta/campaign.db
```

You can point the app at a different database with `STA_DB_PATH`:

```bash
STA_DB_PATH=/path/to/campaign.db python3 sta.py
```

## Export

Use the dashboard export action or press `e` to export Markdown files. The default export location is:

```text
~/campaign_vault
```

A toggle on the export screen controls whether full character sheets and
active effects are included (as structured YAML frontmatter plus a
readable summary) or left out for a lighter, narrative-only vault.

## Markdown Vault Import

A vault exported by this app (not an arbitrary hand-authored Obsidian vault)
can be imported back in from the Backup & Restore screen (`b` on the
dashboard), or replace all current data. This round-trips entities, notes,
relationships, character sheets, and active effects losslessly when the
vault was exported with stats included.

## JSON Backup And Restore

The full-fidelity path: entities, relationships, character and ship sheets, the
Momentum/Threat pools, the current mission's Directives and scene Traits, any
Extended Tasks, and the Talents, Focuses, adversary and spaceframe libraries.

Backups written before this (format version 1) still restore. They carry no
record of the pools or the libraries, so those are left as they are rather than
cleared.

Create a backup:

```bash
python3 sta.py --backup-json backup.json
```

Restore into an empty database:

```bash
python3 sta.py --import-json backup.json
```

Replace the current database contents during restore:

```bash
python3 sta.py --import-json backup.json --replace
```

## Development

Install development dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
python3 -m pytest
```
