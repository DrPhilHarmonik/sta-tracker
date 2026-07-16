# LCARS Tracker — Star Trek Adventures 2e Fork Roadmap

A planning document for forking **DM Tracker** into a campaign manager for
**Star Trek Adventures, 2nd Edition** (Modiphius 2d20 system). No code has been
written yet; this is the design + phase plan.

The guiding principle: the DM Tracker already isolates its D&D 5e rules from a
system-agnostic campaign core. This fork **keeps the core, replaces the rules
layer**, and adds the one structural piece 2d20 needs that 5e never did (shared
Momentum/Threat pools). Terminology below uses STA 2e names (Departments, not the
1e "Disciplines").

---

## What ports over unchanged

These carry from the parent project with, at most, content (not machinery)
changes. Do not rewrite them:

- `db.py` — entity/relationship CRUD, JSON backup/restore, `replace_all`, the
  single `normalize_special_fields` validation chokepoint. The character sheet is
  an opaque JSON blob in `fields["sheet"]`; the DB never inspects its shape, which
  is what makes this a fork and not a rewrite.
- Relationship graph + `screens/relationships.py`.
- `campaign_manager.py`, dashboard, global search, quick-capture, session
  workflow, quest objectives.
- `export.py` Markdown/Obsidian vault export/import — structurally generic.
- The entity machinery in `models.py` (schemas' *content* changes; the mechanism
  does not).

## What gets deleted outright

STA 2e has no equivalent, so these go away rather than getting ported:

- `xp.py` — advancement is **milestone-based** (Values / Focuses / Talents /
  attribute bumps), not XP thresholds.
- `rest.py` — no hit dice / long rest; Stress recovers narratively and between
  scenes.
- `encounter_gen.py`, `encounter_balance.py` — no CR budget math. Adversary
  balance in STA is narrative + Threat economy, not a points formula.

## What gets replaced (the rules layer)

- `sheet.py` → STA character sheet shape.
- `dice.py` → 2d20 task resolution + Challenge Dice.
- `combat.py` → STA action/turn model + Stress/Injuries.
- `classes.py` / `races.py` → Species + Career/Track + Role reference data.
- `srd.py` / `data/monsters.json` → NPC/adversary and starship stat blocks
  (user-authored — see licensing note).
- `conditions.py` / `effects.py` → STA Conditions & Traits.
- `screens/wizard.py`, `screens/sheet.py`, `screens/combat.py` → rewritten UIs.

---

## Confirmed design decisions

- **Ruleset:** Star Trek Adventures 2e (Modiphius 2d20). Attributes: Control,
  Daring, Fitness, Insight, Presence, Reason (range ~7–12). Departments: Command,
  Conn, Engineering, Security, Medicine, Science (range 0–5).
- **Task resolution:** roll 2d20, each die ≤ (Attribute + Department) scores a
  success; a natural 1 scores 2 successes (Critical); a natural 20 is a
  Complication. Meeting the Difficulty succeeds; extra successes become Momentum.
  A **Focus** raises the Critical range (success on that die's value ≤ target *and*
  ≤ the relevant Discipline counts as 2). The app computes successes; the GM sets
  Difficulty.
- **Challenge Dice ([CD]):** d6 with STA faces — 1 = 1, 2 = 2, 3/4 = 0, 5/6 =
  1 + Effect. Used for damage and other variable effects. `dice.py` gains this as
  a first-class die type alongside the d20 pool.
- **Momentum & Threat are table-level shared pools**, not per-character stats.
  This is the one genuinely new structural piece. Store as a **singleton campaign
  state record** (new lightweight `campaign_state` entity type, or a dedicated
  one-row table). Threat seeds at 2× the number of player characters per mission.
- **No HP.** Characters have a **Stress** track (derived from Fitness + Security)
  and take **Injuries** when Stress is exceeded or an attack is made lethal via
  Threat. Starships use **Shields** + **Breaches** instead.
- **Values (4) and Determination.** Each character has narrative Values and a
  personal Determination metacurrency (max 3) that can be spent — often by
  invoking or challenging a Value. Modeled on the sheet, not enforced.
- **Starships are a second sheet type.** A new `starship` entity with its own
  sheet shape: Systems (Comms, Computers, Engines, Sensors, Structure, Weapons),
  the six Departments, plus Shields, Power, Scale, Crew Support, Resistance,
  Breaches. Reuses the entity/sheet machinery; not a special case in the DB.
- **Combat has no initiative roll.** Turn order alternates between the player and
  GM sides; within a side, players choose who acts. The combatant-list scaffolding
  from `combat.py` is reusable; the initiative sort / turn_index math is not.
- **Mechanical enforcement is reference-only** (inherited stance). Conditions,
  Talents, and ship systems surface as reminders; the GM applies consequences.
- **Licensing:** unlike the SRD-backed parent, STA content is copyrighted and has
  no open SRD. Ship **no** bundled Talent text or adversary stat blocks. All such
  content stays user-entered; the engine ships empty. Reference panels describe
  *mechanics* (which are not copyrightable), never reproduce published tables.

---

## Phases

### Phase 1 — Fork & strip

**Status: Done.** Forked to the `sta_tracker` sibling repo (fresh git). Deleted
`xp.py`, `rest.py`, `encounter_gen.py`, `encounter_balance.py` and their
screens/tests; removed the XP/rest/encounter-balance bindings, buttons, and
actions from the dashboard, the XP column from Party Overview, and the CR-budget
balance readout from the combat screen. Relocated the generic `active_adventurers()`
helper from `rest.py` into `db.py`. Renamed product → **STA Tracker** (`STAApp`,
`sta.py`, `sta.tcss`), DB path → `~/.config/sta/`, env var → `STA_DB_PATH`,
manager dir → `~/.local/share/sta_tracker/`. The app boots as a pure campaign
tracker with no rules math. **301 tests passing** (down from 358 — the 57 removed
were the deleted systems' own tests).

### Phase 2 — Dice engine (2d20 + Challenge Dice)

**Status: Done.** Added the STA engine to `dice.py` additively (the generic
`roll()` parser stays; the 5e `roll_d20`/ability/skill helpers stay as
transitional code the combat/roll screens still call until Phases 4/7).

- `roll_task(attribute, department, difficulty, focus, dice, complication_range,
  rng)` → `TaskResult(successes, complications, succeeded, momentum,
  target_number, rolls, detail)`. TN = attribute + department; die ≤ TN scores a
  success; natural 1 or (focus and die ≤ department) scores 2; die in the
  complication range (20 by default) adds a Complication; Momentum = successes −
  Difficulty on success. Pool clamped to `MAX_TASK_DICE` (5).
- `roll_challenge(count, rng)` → `ChallengeResult(total, effects, rolls, detail)`,
  reading Challenge Dice by icon (1→1, 2→2, 3/4→0, 5/6→1+Effect).

Pure functions, seeded-RNG testable, no UI. 14 new tests in
`tests/test_sta_dice.py` (a scripted-RNG helper pins exact faces). **315 tests
passing.**

### Phase 3 — Character sheet shape

**Status: Done.** New module `sta_sheet.py` (not an in-place rewrite of
`sheet.py`). Measuring the blast radius first showed the 5e sheet shape is read
by ~15 screens/modules (wizard, sheet, combat, entities, roll, export, both
importers) all slated for later phases — changing the shape in place would crash
every one of them at once and turn the suite red. So the STA sheet is introduced
**in parallel**, the same additive strategy used for the dice engine: each
consumer migrates onto `sta_sheet` in its own phase (sheet screen P4, wizard P6,
combat P7, export P10), and `sheet.py` is deleted when the last reader is gone.
The DB chokepoint is untouched this phase (no STA sheets are persisted yet).

`sta_sheet.py` provides `default_sheet()` / `normalize_sheet()` for the 6
Attributes, 6 Departments, Focuses, Values, Talents, Stress (base = Fitness +
Security, with a preservable `stress_max` override for talent/gear bonuses),
Determination (0–3), plus weapons, injuries, protection, and species/rank/
career/role flat fields. Derived math: `target_number()` (Attribute + Department),
`base_stress()`, `weapon_dice()` (rating + Security), `has_focus()` (feeds the
2d20 critical range). No copyrighted content is bundled — Talent/Value text is
user-entered; only mechanics live here. 15 new tests in `tests/test_sta_sheet.py`,
including a seam check into `dice.roll_task`. **330 tests passing.**

### Phase 4 — Sheet screen

**Status: Done.** Rewrote `screens/sheet.py` as an STA sheet reading from
`sta_sheet`. Tabs: **Stats** (Attributes + Departments input grids with a live
base-Stress readout), **Profile** (species/rank/career/role, Determination,
Protection, Stress max/current, equipment, notes), **Focuses & Values**
(add/remove lists), **Talents & Weapons** (talents; weapons showing computed
`rating + Security` damage dice; injuries), and **Task Roll** — pick an
Attribute + Department + Difficulty + Focus + dice pool and call
`dice.roll_task`, plus a Challenge Dice roller. Class name and `#btn-export-sheet`
preserved so existing screens/tests keep driving it.

**DB bridge:** `db.normalize_special_fields` now dispatches sheet normalization
by shape (`attributes`/`departments` → `sta_sheet`, else the legacy 5e `sheet`),
so both shapes coexist while the other consumers migrate. The 5e branch and
`sheet.py` are removed in Phase 10 once the last reader is gone.

**Transitional friction handled:** the still-5e combat/export/roll screens read
the 5e shape, so an STA-sheeted character shows default HP/AC there and its STA
stats don't yet reach the vault frontmatter — the affected e2e assertions were
updated with comments pointing at Phases 7/10. The obsolete "level syncs to flat
field" test was replaced with an STA attribute-persistence test. 6 new tests
(`tests/test_ui_sta_sheet.py`, plus the DB-bridge path). **335 tests passing.**

### Phase 5 — Momentum / Threat pool (new structural piece)

Add the singleton campaign-state record and a small always-visible pool widget
(Momentum and Threat counters with spend/add). Wire Momentum generation from
`roll_task` results into the pool. This is the only schema addition beyond the
sheet blob; keep it minimal.

### Phase 6 — Chargen wizard

Rewrite `screens/wizard.py` for STA lifepath-style creation: Species → Environment
→ Upbringing → Career/Track → Role, distributing Attribute/Department points and
picking Focuses/Values/a Talent along the way. Species/track reference data
(`species.py`, replacing `races.py`/`classes.py`) — mechanics and point spreads
only, no copyrighted flavor text.

### Phase 7 — Conflict tracker (combat)

Rewrite `combat.py` + `screens/combat.py`: side-alternating turn model (no
initiative sort), Stress/Injury tracking instead of HP, Challenge-Dice damage
rolls, condition/Trait tags, and Momentum/Threat spends surfaced inline
(e.g. buy extra d20, make an attack lethal). Reuse the combatant-list scaffolding;
replace the turn-order engine.

### Phase 8 — Adversary & NPC reference

Replace `srd.py` with a user-authored adversary/NPC library (Minor NPC / Notable
NPC / Major NPC tiers, which drive how much Stress and how many Values they get).
"Add to conflict" flow analogous to the parent's Add-to-Campaign. Ships **empty**;
the GM enters their own stat blocks. Reference panel explains the NPC tiers'
mechanics.

### Phase 9 — Starships

New `starship` entity type + starship sheet shape (Systems, Departments, Shields,
Power, Scale, Breaches) and a starship sheet screen. Extend the conflict tracker
with a ship-combat mode (ranges/zones, power spend, breaches → system damage).
Ships participate in the same entity/relationship/export machinery as characters.

### Phase 10 — Conditions, Traits & export polish

Port `conditions.py`/`effects.py` to STA Conditions and scene/character **Traits**
(narrative tags that adjust Difficulty). Update `export.py` frontmatter/summaries
for the STA sheet + starship shapes so the Obsidian vault round-trips. Full
regression pass; screenshot review pass (mirroring the parent's TUI review
discipline).

---

## Open questions to resolve before Phase 6

- **Chargen depth:** full lifepath (Species→Environment→Upbringing→Career→Role
  with all point steps) vs. a lighter "spend the points" fast path. The parent
  chose Standard Array over full 5e chargen for similar reasons — a lighter path
  may fit the tool's DM-facing scope better.
- **Determination/Value enforcement:** pure tracker vs. prompting to invoke a
  Value on a spend. Recommend tracker-only, consistent with the parent's
  reference-only stance.
- **Ship-vs-character shared conflict:** one unified conflict tracker handling both
  scales, or a separate ship-combat screen. Phase 9 assumes unified with a mode
  toggle; revisit if the turn models diverge too much.
