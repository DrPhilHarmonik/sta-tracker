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

**Status: Done.** `export.export_session_log(path)` renders every session in
timeline order into one `Session Log.md`: each session becomes a heading with
its Stardate / in-game & real dates / location, the related cast
(npc/adventurer/enemy/starship/faction/location) as `[[wikilinks]]`, and its
full notes (or "*No log recorded.*"). The export screen gained an **Export
Session Log** button that writes it into the vault directory. 372 tests
passing.

### 17c — Reputation & Reprimand

**Status: Done.** The character sheet gained `reputation` (0–20, default 1) and
`reprimands` (≥0), normalized like `determination`. New `advancement` helpers
`adjust_reputation` / `adjust_reprimands` / `end_of_mission` clamp the tracker's
bounds (mechanics only — no reproduced progression table). Both fields edit on
the sheet's Profile tab and export in the character stat block. The
`MilestoneScreen` (already the per-character between-missions screen) gained a
**Between Missions: Reputation & Reprimands** section with a live readout and an
**Apply End of Mission** button that shifts both, writing back to the sheet. 380
tests passing.

**Phase 17 complete.** Timeline, session-log export, and Reputation/Reprimand
all shipped.

---

## Batch 2 — deepen play (Phases 18–20)

The table loop is feature-complete; Batch 2 sharpens the parts the GM touches
most. Ordered **mechanics-first**: the two engine-deepening builds (18, 19)
before the search/filter usability work (20). Same working principles as
Batch 1 — additive, one concern per phase, suite green + a commit per phase with
the test count reported.

### Phase 18 — Richer dice roller

**Why:** The 2d20 engine is solid but the *spend* side of Momentum/Threat is
still manual — the GM eyeballs the pool and adjusts counters by hand. This turns
the metacurrency economy into inline affordances on the roll itself.

**Scope:**
- On every Task roll (character sheet, both conflict trackers): a **complication
  range** preset (1 / 2 / 3) feeding `roll_task`'s existing `complication_range`
  parameter, and a **buy dice** control that adds d20s up to `MAX_TASK_DICE` (5),
  debiting the group Momentum pool (2 per die is the usual cost) or adding Threat
  when the group buys on credit — written back through the `PoolBar` /
  `db.adjust_momentum` / `adjust_threat` chokepoints.
- A **Momentum spend menu** surfacing the common Immediate spends (extra die,
  bonus [CD] of Effect, obtain information, keep the initiative) as one-click
  debits that log to the conflict log — reminder-only text plus the pool math,
  no rules enforcement.
- **Keep the pool:** repeat the last Task with the same Attribute + Department +
  Difficulty + Focus so a repeated check (or an Extended Task attempt) is one
  press.

**Non-goals:** no change to the pure `roll_task` result shape; this is spend
accounting + UI on top of the existing engine and pools.

**Status: Done.** New pure `momentum` helpers: `bonus_dice_cost` (escalating
1/3/6 for 1–3 bought dice) and `pay_for_bonus_dice` (spend Momentum first, buy
the shortfall on credit by adding Threat), plus a `MOMENTUM_SPENDS` reminder
list. All three roll surfaces — the character sheet Task Roll and both conflict
trackers — gained a **Complication-range** preset (1 / 2 / 3, feeding
`roll_task`'s existing parameter), a **bought-dice** selector that debits the
pools through `db.get_pools`/`set_pools` and reports the cost, and a **Spend
Momentum** picker of common Immediate spends that debits the pool (and logs, in
the trackers). The character sheet also gained a **Repeat Task** button (keep
the pool — re-roll with the same selectors). Reminder-only: nothing is enforced.
393 tests passing.

### Phase 19 — Ship crew stations & officer substitution

**Why:** The deferred Phase-14b follow-up. A ship currently rolls its own
System + Department; in play the *officer at the station* matters — their
Department and Focus should drive the roll. Finishes the starship conflict loop.

**Scope:**
- Extend the `ship_combat` per-ship record with a **stations** map (bridge
  station → assigned crew entity id) alongside the existing Power/Breach/Trait
  state, through `normalize_ship_combat` so old encounters still load.
- On the ship Task roll in `ShipConflictScreen`, pick the acting officer; the
  roll uses the **officer's Department + the ship's System** (and the officer's
  Focus for the critical range), instead of the ship's own Department.
- Surface who is crewing which station in the Ships tab; log the officer by name
  on each roll.

**Non-goals:** no new turn model (reuses the side-alternating engine); no auto
crew generation (assign from existing adventurers/NPCs).

**Status: Done.** Each `ship_combat` per-ship record gained a `stations` map
(Department key → officer entity id), normalized so old encounters load, with
pure `assign_station` / `clear_station` / `assigned_officers` helpers. The Ships
tab gained a **Crew Stations** section (pick ship + station + officer, Assign /
Clear, with a live assignment readout); the Conflict tab's ship Task roll gained
an **Acting Officer** picker (populated from the acting ship's crew) and an
**Officer Focus** picker. When an officer acts, the roll uses their Department +
Focus with the ship's System (otherwise the ship's own Department), and the log
/ result name the officer and station. The conflict summary lists each ship's
crew. 399 tests passing.

**Phase 19 complete.** The starship conflict loop now models who is at the
bridge.

### Phase 20 — Cross-sheet search & list filters

**Why:** Global search (`db.search_all`) and the entity lists only match name and
notes today, so a Focus, Talent, species, or Trait living in the sheet blob is
invisible to search — the GM can't answer "who has Warp Field Dynamics?" fast.

**Scope:**
- Extend search to look **inside the sheet blob** (Focuses, Values, Talents,
  species/rank/role, and starship systems/traits) so `GlobalSearchScreen` and
  the per-type list search find sheet content, with a note on the match.
- Add **column filters** to `EntityListScreen` (by status / kind / type — the
  flat schema selects already in `models.py`), so long lists narrow quickly.
- Keep it read-only and additive: the DB stays the source of truth; this is a
  richer read path, no schema change.

**Non-goals:** no full-text index or fuzzy ranking; substring match over the
normalized sheet is enough at this scale.

**Status: Done** (408/408). New `search.py` flattens sheet content
(Focuses/Values/Talents, species/rank/role, ship Talents/Traits) into labeled
terms; `db.search_all` and per-type `db.list_entities` search now match name,
notes, and sheet, and `search_all` annotates each hit with a `match` label.
`GlobalSearchScreen` gained a "Match" column; `EntityListScreen` gained
column filters for its select-type schema fields (Status/Kind/Type/Difficulty).

## Batch 3 — between missions & at the table (Phases 21–22)

Two additive phases, mechanics before utility (matching the Batch 2 ordering).
21 gives the group a clean way to close out a scene/mission -- recover Stress
and Injuries, decide whether Threat carries over; 22 turns the sheet data
already in the DB into a compact play aid you can print or keep open at the
table. Both are read/append only over existing state -- no schema change.

### Phase 21 — Recovery & Threat carry (between scenes/missions)

**Why:** The tracker can spend Stress, add Injuries, and bank Threat during
play, but nothing helps the group *reset* between scenes or missions. Today a
GM hand-edits every character's `stress_current` back up and manually zeroes
Threat. STA has light, real procedures for this (Stress resets at the end of a
scene; Injuries need a Medicine Task / downtime; Threat may reset or carry at
the GM's call) and they deserve a one-button flow.

**Scope:**
- New pure `recovery.py`: `recover_stress(sheet)` (restore `stress_current`
  to `stress_max`), `clear_injury(sheet, index)` / `clear_all_injuries(sheet)`,
  and a `recover_sheet(sheet, *, stress=True, injuries=False)` convenience that
  returns a new normalized sheet. Keep it a pure transform over the sheet dict,
  mirroring `advancement.py`.
- `threat_between_missions(threat, carry)` helper (in `momentum.py`, next to
  the existing seed/clamp logic): return `threat` unchanged when `carry` is
  True, else 0 -- the GM's reset-or-carry decision, made explicit.
- A **"Between Scenes / Recovery"** section: end-of-scene "Recover Stress (all
  active PCs)" action, per-PC injury clearing, and a Threat "Reset to 0 / Carry
  over" control tied to `db.set_pools`. Reuse the milestone screen's
  between-missions block or add a sibling section there; keep the wiring thin.

**Non-goals:** no automated Medicine Tasks or downtime economy, no per-injury
severity model -- clearing an Injury is a GM-confirmed edit, not a dice check.

**Status: Done** (423/423). New pure `recovery.py` (`recover_stress`,
`clear_injury`, `clear_all_injuries`, `recover_sheet`) and
`momentum.threat_between_missions(threat, carry)`. The recovery UI landed on
the **Party Overview** screen (it already lists every active PC's Stress and
Injuries): "Recover Stress -- All", "Clear Injuries -- Selected" (row cursor),
and Threat "Carry Over" / "Reset to 0" wired to `db.set_pools`.

### Phase 22 — Printable one-page play aids

**Why:** `export.py` can already write a full Obsidian vault and a session log,
but there's no compact, at-the-table reference: a single page per character or
ship with just the numbers you reach for mid-roll (Attributes/Departments or
Systems, Focuses, Values, Stress/Determination, weapons). GMs print these or
keep them open beside the tracker.

**Scope:**
- New `export.export_play_aid(entity_id, output_path=None)` producing a tight,
  single-page Markdown play aid, reusing `_format_character_markdown` /
  `_format_starship_markdown` but trimmed to the play-critical block (no
  relationship graph, no notes dump). Factor shared rendering rather than
  duplicating the sheet formatters.
- `export.export_all_play_aids(output_dir)` writing one file per adventurer +
  starship (the entities you actually bring to the table), returning a count.
- A **"Play Aids"** button on the backup/export screen next to "Export Session
  Log", writing to `<path>/Play Aids/`.

**Non-goals:** no PDF/HTML rendering or print-CSS -- Markdown only, same as the
rest of `export.py`; no layout engine, just a disciplined section order.

**Status: Done** (429/429). `export.export_play_aid(entity_id, path=None)` and
`export.export_all_play_aids(output_dir)` (one file per adventurer + starship).
The sheet formatters gained a `compact` flag reused by `_render_play_aid` --
trims the ## heading, the Reputation/Reprimands line and the Milestone log for
characters; the full vault output is unchanged. A "Play Aids" button on the
Export screen writes to `<path>/Play Aids/`.

## Later / optional

- Reputation/Reprimand deepening (promotion thresholds, per-mission prompts)
  beyond 17c.
- UX polish: keyboard-help (`?`) overlay, LCARS theming.

(Between-scenes recovery / Threat carry and printable play aids were promoted
to Batch 3 as Phases 21 and 22.)

---

## Sequencing rationale

11 first (small, finishes the economy), then 12 (growth loop) and 13 (cheap
speed-up) in either order, before committing to 14 (the multi-session ship-combat
build). 15/16 are additive and can slot in whenever. Nothing here blocks anything
except 16's spaceframe builder, which wants 13's library pattern in place.
