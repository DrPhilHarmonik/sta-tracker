# STA Tracker — Forward Roadmap

The migration from the D&D 5e DM Tracker is complete (see `STA_FORK_ROADMAP.md`,
Phases 1–10, all done). This document plans **new capability** for the
standalone Star Trek Adventures 2e tracker.

## Working principles (unchanged from the migration)

- **Additive, one concern per phase.** Each phase is a self-contained slice
  that leaves the full test suite green and the app bootable. Commit per phase
  with the test count reported.
- **Mechanics only, no bundled content.** STA has no open SRD. We ship rules
  math (which isn't copyrightable) and empty, user-authored libraries; the GM
  enters any Talent/adversary/spaceframe text themselves. Follow the
  `adversaries.py` precedent for every new reference library.
- **The sheet blob is the source of truth.** New per-character/ship data goes in
  `fields["sheet"]` through the shape-aware `db._normalize_sheet_any` chokepoint;
  campaign-wide state (like the Momentum/Threat pools) goes in the
  `campaign_state` singleton. Avoid new flat schema columns unless a list view
  needs them.
- **Match existing patterns.** Reuse the `PoolBar`, the wizard step engine, the
  `adversaries` library shape, and the conflict-tracker scaffolding rather than
  inventing parallel structures. Read 2–3 neighbours before writing.

---

## Phase 11 — Close the metacurrency loop: Determination & Values

**Why:** Momentum and Threat are fully wired (Phase 5); Determination is still
an inert integer on the sheet, and Values are a plain list. Determination is the
most conspicuous dead stat in the tool.

**Scope:**
- `sta_sheet` helpers for spending/regaining Determination (0–3 cap already
  exists). Spending 1 adds a d20 to a Task that automatically scores 1 success
  (extend `dice.roll_task` with a `bonus_successes`/auto-success parameter, or a
  thin wrapper — keep the pure engine testable).
- On the character sheet and in the conflict tracker's Task roll, an "Invoke
  Value (spend Determination)" and "Challenge Value (regain Determination)"
  affordance tied to the character's Values list.
- Log Value invocations/challenges to the conflict log.

**Non-goals:** no new entity type or schema; this is UI + engine wiring.

**Status: Done.** `dice.roll_task` gained a `determination` parameter: each
point prepends a bonus d20 set to a natural 1 (an automatic critical, two
successes) that never generates a Complication. `sta_sheet.adjust_determination`
is the pure 0–3 clamp helper. The character sheet's Task Roll tab has a Value
picker, an "Invoke (spend 1 Det)" switch that decrements Determination and adds
the bonus die on the roll, a "Challenge Value (+1 Det)" button, and a live
Determination readout. The conflict tracker mirrors this for the acting
character (writing Determination back to their sheet and logging both invoke and
challenge to the conflict log). 278 tests passing.

## Phase 12 — Milestones & advancement

**Why:** STA has no XP. Characters change through Milestones (Spotlight / Arc /
Career). Right now a character can never grow — the single biggest missing loop.

**Scope:**
- A per-character milestone log (list of `{type, date, note}`) on the sheet.
- A guided "apply a milestone" flow: swap one Attribute point, swap one
  Department point, change a Focus, or (Arc/Career) add a Talent / adjust the
  spread within the STA limits. Validate against the same bounds the wizard uses.
- Surface milestone history on the sheet and in the export stat block.

**Status: Done.** New `advancement.py` holds the pure, validated edits a
Milestone grants — swap/increase Attributes (bounds 7–12) and Departments
(0–5) — raising a clear `ValueError` rather than silently clamping. The sheet
gained a `milestones` log (`{type, date, note}`), normalized in `sta_sheet`. A
new `MilestoneScreen` (reached via **Milestones** / `M` on an adventurer's detail
screen, adventurer-only) records a milestone and applies one advancement per
click — attribute/department swap or increase, add a Focus, add a Talent (both
remembered in the Phase-13 libraries), or a note-only entry — logging a summary
with the date and refusing illegal edits without touching the sheet. Milestone
count shows in the detail summary and the full history exports to the vault stat
block. 312 tests passing.

## Phase 13 — Reference libraries for Talents & Focuses

**Why:** Cheapest win. Chargen and the sheet are slower than they need to be
because every Talent and Focus is free text.

**Scope:**
- Clone the `adversaries.py` shape into `talents.py` (name + short user-authored
  description) and a lightweight `focuses.py` suggestion store, each persisted as
  JSON next to the campaign DB and shipping empty.
- Autocomplete/pick from these in the wizard's Focuses/Talents steps and on the
  character + starship sheets. A small reference screen to manage them (reuse the
  `MonsterRefScreen` list/detail layout).

**Status: Done.** New `library.py` factors out the JSON-next-to-the-DB
persistence (isolated per config dir / per test `tmp_path`); `talents.py`
(`{name, description}`, upsert-by-name) and `focuses.py` (deduped strings) layer
on top, both shipping empty. The libraries **self-populate**: adding a Focus or
Talent on the character sheet, the starship sheet, or in the wizard remembers it
(blank/duplicate adds are no-ops), so the picker gets richer as you play. The
character and starship sheets gained an "Add from Library" Select next to the
free-text add. New `ReferenceScreen` (Talents / Focuses tabs, `T` on the
dashboard) browses, describes, and prunes them. 294 tests passing.

## Phase 14 — Starship conflict mode  *(large — the deferred feature)*

**Why:** The headline STA subsystem we punted on in Phase 9. Ships exist as a
sheet type but can't fight.

**Scope:**
- A ship-conflict tracker parallel to the personal one: zones / range bands,
  **Power** as a spendable per-ship pool, Shields → **Breaches** → System damage,
  and crew assigned to bridge stations rolling System + Department.
- Reuse the side-alternating turn engine from `combat.py`; add a ship-scale
  damage/Breach model alongside the existing Stress helpers.
- Momentum/Threat (the `PoolBar`) already applies at the table level — surface it
  here too.

**Note:** biggest build in this roadmap; likely splits into 14a (model) / 14b
(screen) like the character conflict tracker did.

**Status: Done** (split 14a/14b as expected). **14a** — new `ship_combat.py`
model, parallel to `combat.py`: side-alternating ship turns, a shared range band
(Close/Medium/Long), per-ship **Power** that refills to the ship's Engines rating
each round, pure `apply_ship_damage` returning (new shields, overflow), per-ship
**Breaches** by system, and ship Traits. Stored in an encounter's
`fields["ship_combat"]` via a new DB special field + normalizer. **14b** — new
`ShipConflictScreen` (Ships / Conflict / Turn Controls / Log tabs) reached from
an encounter's detail via **Ship Conflict** / `O`, so one encounter can host a
personal *or* a ship conflict. Damage flows Resistance (= Scale) → Shields (on
the ship sheet, like Stress) → Breaches (overflow auto-assigned to a chosen
system); weapon damage rolls Challenge Dice off the ship sheet and pre-fills the
apply field; ship Task rolls use System + Department and bank Momentum / add
Threat like the personal tracker; the Phase-5 `PoolBar` is mounted inline.
Crew-officer station substitution on the Task roll is a noted follow-up.
330 tests passing.

## Phase 15 — Extended Tasks, Directives & scene Traits

**Why:** Rounds out the task system beyond single rolls, and gives the conflict
tracker real Difficulty modifiers to read.

**Scope:**
- An Extended Task tracker: Work track, Magnitude, Resistance, breakthroughs.
- Mission **Directives** and **scene Traits** as first-class, table-visible tags
  (campaign-state or encounter-scoped) that the Task roll UI can factor into
  suggested Difficulty.

**Status: Done.** New `extended.py` tracks Extended Tasks (Work total/done,
Magnitude, base Difficulty + Resistance, with `effective_difficulty` and
`add_work` capping/completion), persisted next to the DB. New `scene.py` holds
the mission's Directives and the scene's Traits in a `scene.json` dict (deduped,
per-campaign). A new `SceneScreen` (Extended Tasks / Directives & Traits tabs,
`D` on the dashboard) manages all three. Both conflict trackers echo the active
Directives/Traits in their summary via `scene.summary_lines()`, keeping them
table-visible during play so the GM factors them into Difficulty. 346 tests
passing.

## Phase 16 — Supporting Characters & spaceframe builder

**Why:** Fast table prep. Both lean on the Phase 13 library pattern.

**Scope:**
- Lightweight "quick crew" creation (STA Supporting Characters) — a trimmed
  wizard path that spits out a usable adventurer/NPC fast.
- A template-driven starship builder: pick a saved spaceframe template, get its
  Systems/Scale spread pre-filled on a new starship.

**Status: Done.** New `supporting.py` builds a Supporting Character's STA sheet
(a lighter base spread with the species' fixed Attribute bonuses, optional Focus
and role); `QuickCrewScreen` (one-step form, "Quick Crew" on the Adventurers
list) creates one and drops you on its sheet. New `spaceframes.py` is a
user-authored spaceframe library (ships empty, `save`/`from_entity`/`build_sheet`
mirroring `adversaries.py`); `SpaceframeScreen` ("Spaceframes" on the Starships
list) snapshots a campaign ship into a reusable frame and builds new ships from
saved frames (recomputing Shields from the frame's Structure). 360 tests
passing.

---

## All forward phases (11–16) complete

Phases 11–16 are shipped. The tracker now covers the full STA 2e table loop:
Momentum/Threat + Determination (invoked via Values), Milestone advancement,
self-populating Talent/Focus libraries, personal *and* starship conflict
tracking, Extended Tasks with Directives/scene Traits, and one-step Supporting
Characters plus a spaceframe builder. 360 tests passing.

## Phase 17 — Campaign timeline, session-log export & Reputation

**Why:** The between-missions layer the tool lacked. Pulls the first item out of
the "Later / optional" bucket into a proper phase, split 17a/b/c by concern.

### 17a — Stardate campaign timeline

**Status: Done.** The `session` schema gained a **Stardate** field (alongside the
real date and in-game date). New pure `timeline.py` gathers the `session`
entities into ordered rows (number · Stardate · in-game date · real date ·
location · a one-line recap = the first non-blank note line), sorted by session
number with unnumbered sessions falling to the end. New `TimelineScreen`
(**Timeline** / `L` on the dashboard) renders them in a DataTable with an
empty-state prompt; selecting a row opens that session's detail. 367 tests
passing.

### 17b — Session-log export

**Planned.** A campaign session-log Markdown document rendered in timeline order,
surfaced on the export screen.

### 17c — Reputation & Reprimand

**Planned.** `reputation`/`reprimands` on the character sheet with a
between-missions apply flow and export stat-block surfacing.

## Later / optional

- Reputation/Reprimand deepening (thresholds, per-mission prompts) beyond 17c.
- Richer dice roller: buy extra d20s from Momentum inline, "keep the pool" for
  repeated Tasks, complication-range presets.
- UX polish: cross-sheet search, list filters, keyboard-help overlay, theming.

---

## Sequencing rationale

11 first (small, finishes the economy), then 12 (growth loop) and 13 (cheap
speed-up) in either order, before committing to 14 (the multi-session ship-combat
build). 15/16 are additive and can slot in whenever. Nothing here blocks anything
except 16's spaceframe builder, which wants 13's library pattern in place.
