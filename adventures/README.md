# Adventures

Importable, ready-to-run adventures for the STA Tracker. Each is a full-fidelity
JSON backup (entities, relationships, character/ship sheets, quest objectives).

## Silence at Erevos  (`silence_at_erevos.json`)

A **2–5 session** Star Trek Adventures 2e mystery-horror-first-contact episode.
Original content — nothing reproduced from published material.

**The pitch:** the crew answers a dying distress call from a Federation
listening post at the edge of the Kavari Expanse and finds it dark and empty.
The trail leads to an ancient alien derelict whose *Whisper Beacon* has been
calling for help for ten thousand years — and drives listeners to paranoia and
then devotion. A Syndicate salvage crew is racing them to the prize, and a
missing doctor already speaks for the Beacon. It ends on a genuine Star Trek
choice, not a boss fight.

**What's inside (26 entities, 19 relationships):**

- **2 starships** — the players' science surveyor *USS Wayfarer* (Scale 4) and
  the antagonist raider *Cinder* (Scale 3), both with full ship sheets.
- **3 adversaries** — Draex Kol (Major NPC), a reusable Ashfall Enforcer
  (Notable), and a tragic Signal-Maddened Crewman (Minor), all with STA sheets.
- **3 NPCs**, **3 locations**, **2 factions**, **2 items**, **3 quests** (main +
  two side quests, with objectives), and **4 encounters** (including a personal
  Conflict and a Ship Conflict).
- **4 session outlines** (split session 4 into 4+5 if your table runs long),
  each with beats, twists, and GM notes in its Notes field.

**Uses the tracker's systems:** set the suggested Mission **Directives** and
scene **Traits** on the Scene screen; run the **Ship Conflict** in "Standoff over
the Expanse"; run the **Extended Task** "Silence the Whisper Beacon" at the
climax; lean on **Challenge Value → regain Determination** as the signal frays
the crew; award a **Milestone** to each character in the aftermath.

### How to import

The importer refuses to load into a campaign that already has data, so import
into a **fresh** campaign.

**In the app (recommended):**
1. Dashboard → **Switch Campaign** (`Ctrl+W`) → create/select a new empty
   campaign.
2. Dashboard → **Backup / Restore** (`b`) → put the path to
   `adventures/silence_at_erevos.json` in the *Restore file path* field →
   **Restore (into empty DB)**.

**From the command line:**
```bash
python sta.py --import-json adventures/silence_at_erevos.json
# ...into a fresh campaign DB. Add --replace to OVERWRITE the current one:
python sta.py --import-json adventures/silence_at_erevos.json --replace
```
`--replace` erases the active campaign first — only use it on a scratch campaign.

After import, assign the *USS Wayfarer* to your players (or swap in their own
ship) and start with **Session 1 – Distress at Erevos**.
