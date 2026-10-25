# formats

The tournament formats the bot can run. Each `.json` file here (except `schema.json`) is one format: the rules of the pre-game phase of one tournament or ranked mode. Contributors add a format by adding a file, with no code change.

| File | What it is |
|---|---|
| `el-classico.json` | A format made for development, to be replaced by real tournaments: a best-of-1 with three templates, where A bans one, B bans one, and the template that is left is played. The smallest working example. |
| `mp2026.json` | Mistrzostwa Polski 2026: a group phase (best of 1, three templates), an elimination phase (best of 3, seven templates) and a final (best of 3, all nine). A larger example with phases that use different parts of one template list. |
| `schema.json` | Describes the shape a format file must have: which fields exist, which are required, which values are allowed. Every field has a `description` in it. |

## Add a format: the short version

1. Copy an existing tournament file that is close to yours (one with the same number of phases is best) to `formats/<your-id>.json`. The file name must be the same as the `id` inside, for example `spring-cup.json` with `"id": "spring-cup"`.
2. Edit the copy: `id`, `name`, the `templates` of the tournament, and its `phases`.
3. Check it. Either run the tests, or start the bot, which checks every file first and prints every problem it finds without needing a token:

   ```powershell
   poetry run pytest
   ```

   Once the bot runs, `/info mode:<your mode>` shows how players will see your tournament.
4. Open a pull request.

## A complete example

Two phases, with a setting at each level. Everything below explains it piece by piece.

<!-- full example -->
```json
{
  "id": "spring-cup",
  "name": "Spring Cup",
  "roll_rules": { "roll_cost": 300 },
  "allowed_towns": ["castle", "rampart", "tower", "inferno", "necropolis", "dungeon", "stronghold", "fortress", "conflux"],
  "templates": [
    "JC",
    "6lm10a",
    { "template": "h3dm1", "roll_rules": { "roll_cost": 0 } },
    "Diamond",
    "Sapphire"
  ],
  "phases": [
    {
      "name": "Groups",
      "best_of": 1,
      "pool": ["JC", { "template": "6lm10a", "roll_rules": { "rolls_per_player": 2 } }, "h3dm1"],
      "template_selection": {
        "type": "sequence",
        "steps": [
          { "who": "A", "do": "ban" },
          { "who": "B", "do": "ban" },
          { "do": "decider" }
        ]
      }
    },
    {
      "name": "Final",
      "best_of": 3,
      "template_selection": {
        "type": "sequence",
        "steps": [
          { "who": "A", "do": "ban" },
          { "who": "B", "do": "ban" },
          { "who": "A", "do": "pick" },
          { "who": "B", "do": "pick" },
          { "do": "decider" }
        ]
      }
    }
  ]
}
```

## The tournament

| Field | Meaning |
|---|---|
| `id` | Lowercase words joined by dashes. Same as the file name. |
| `name` | The name players see. |
| `status` | `active` (default) or `archived`. Archived formats stay in the repository and can still be looked up with `/info`, but cannot start new matches. **Never delete a finished tournament, archive it.** |
| `thread_visibility` | `public` (default) or `private`. Who can read the match thread. |
| `templates` | Every template used in the tournament, each once. |
| `phases` | One or more phases, for example group stage and final. |
| `roll_rules`, `allowed_towns` | Optional settings for the whole tournament, see below. |
| `settings` | Optional: the timer and the recommended simultaneous turns for the whole tournament, see below. |
| `description`, `additional_rules` | Optional free text (1 to 1000 characters each) about the tournament as a whole, shown by `/info <mode>`. Rules for one template are written as that template's `additional_rules` setting instead. |

## Templates, and which phase uses which

`templates` lists the templates of the whole tournament once. Write a template's id (`"JC"`). The ids and display names are in [`../data/templates.json`](../data/templates.json); players see the display name (Jebus Cross) and may type either.

Each phase chooses from that list with its own `pool`. **Leave `pool` out and the phase uses every template of the tournament**, which is what the Final does above. The Groups phase names three of the five.

A template's **difficulty** is not written in a format. It belongs to the template (`data/templates.json`), because that is how the template is played, and it decides the starting gold (80%: 30000, 100%: 20000, 130%: 15000, 160%: 10000, 200%: 0). At 200% the game is all-random and the trade is only a toss for color.

## Roll rules

A roll lets a player pay to get a new pair of towns. Three rules: `roll_cost` (gold, default 500), `rolls_per_player` (default 1) and `max_roll_bans` (towns a player may ban when rolling, default 2).

You can write them in three places. **The most specific one wins, rule by rule**:

```
built-in defaults
  -> the tournament's "roll_rules"
    -> a template in the tournament's "templates" list      (that template, in every phase)
      -> a template in a phase's "pool"                     (that template, in that phase only)
```

In the example: the tournament sets the cost to 300; `h3dm1` is free (cost 0) everywhere; and in the Groups phase `6lm10a` gets two rolls per player (and still costs 300, because that is not overridden). Write only what differs, and leave the rest out.

## Settings: the timer, roads, map size and more

A template states in [`../data/templates.json`](../data/templates.json) what is normally played on it (see [`../data/README.md`](../data/README.md)). A tournament says what it plays with `settings`, written in the same three places as the roll rules, and the most specific one wins, setting by setting:

```
what the template states
  -> the tournament's "settings"                          (only timer and sim_turns)
    -> a template in the tournament's "templates" list    (that template, in every phase)
      -> a template in a phase's "pool"                   (that template, in that phase only)
```

| Setting | Meaning |
|---|---|
| `timer` | **Only ever set here, never in the catalogue.** A chess timer written `12:00+06:00+02:00`: 12 minutes for each player at the start, 6 minutes added at the beginning of each of their turns, and 2 minutes added each time a fight starts. Always `mm:ss`, two digits everywhere, seconds below 60. |
| `sim_turns` | How long simultaneous turns are recommended to last, as `117` or `121` (month, week, day). Any valid date. |
| `roads`, `map_size`, `ai` | The roads, the map size and the number of computer players for **one template**. Each must be one of the values the template allows. A template that states no allowed values for a setting cannot have it chosen: complete its facts in `data/templates.json` first. Not allowed for the whole tournament. |
| `download` | **For one template only**: a link starting with `https://` for the version of the template this tournament plays, when it is not the one built into HotA. It replaces `built_in`, so `/info` and the thread show the link instead of "Built into HotA". |
| `additional_rules` | **For one template only** (never in the tournament's own `settings`): additional rules for the template, free text of 1 to 1000 characters. They replace the rules the template states in the catalogue, and a phase's `additional_rules` replace the list's, like any other setting. Shown by `/info`, and posted in the thread when the trade of a game on the template starts. |

What a setting does not say, the template's default decides, and when that is not stated either, the bot says nothing about it. `/info` shows what is played on a template in your tournament, and the match thread repeats it where the template of a game is announced, with the timer, map size, roads and computer players again in the lobby settings.

The example uses the three templates of the example in [`../data/README.md`](../data/README.md) (`JC`, `6lm10a` and `h3dm1`):

<!-- settings example -->
```json
{
  "id": "spring-cup",
  "name": "Spring Cup",
  "description": "The spring open",
  "additional_rules": "Players may agree on the length of simultaneous turns",
  "settings": { "timer": "12:00+06:00+02:00", "sim_turns": "121" },
  "templates": [
    { "template": "JC", "settings": { "map_size": "XL+U", "ai": 6, "additional_rules": "Ends on turn 133" } },
    "6lm10a",
    "h3dm1"
  ],
  "phases": [
    {
      "name": "Main",
      "best_of": 1,
      "pool": [
        { "template": "JC", "settings": { "timer": "15:00+06:00+02:00", "roads": "fast" } },
        "6lm10a",
        "h3dm1"
      ],
      "template_selection": {
        "type": "sequence",
        "steps": [
          { "who": "A", "do": "ban" },
          { "who": "B", "do": "ban" },
          { "do": "decider" }
        ]
      }
    }
  ]
}
```

Here every template has the 12-minute timer except Jebus Cross in the phase, which has 15 minutes. Jebus Cross is played with extra large underground maps and six computer players, and in this phase on fast roads.

## Allowed towns

By default players can get any town in [`../data/towns.json`](../data/towns.json). `allowed_towns` restricts that, using the town ids (`"castle"`). Written on the tournament it applies to every phase; written on a phase it **replaces** the tournament's list for that phase. A list needs at least two towns, because the bot draws a pair of different towns from it. In the example the whole tournament uses only the nine towns of the original games.

## Template selection

`template_selection` says how a phase chooses its templates.

- **`"type": "agreed"`**: the players agree on the template themselves (ranked games). Nothing else is written, and `best_of` must be 1 in practice.
- **`"type": "sequence"`**: bans and picks in a fixed order. **A** is the coinflip winner and **B** the other player. Each step is `{ "who": "A", "do": "ban" }`, `{ "who": "B", "do": "pick" }`, or `{ "do": "decider" }`: the template that is left, which nobody chooses.

Players write the order as letters: `AB` for "A bans, B bans, then decider". The bot shows it that way in `/info`.

| Sequence | In words | Games |
|---|---|---|
| `AB` | A bans, B bans, then decider | best of 1: the decider |
| `ABAB` | A bans, B bans, A picks, B picks, then decider | best of 3: A's pick, B's pick, the decider |
| `ABBAAB` | A bans, B bans, B bans, A bans, A picks, B picks, then decider | best of 3 with 7 templates |

Three rules a file must follow, and each is checked:

- **Every template in the pool is used by exactly one step:** banned, picked, or taken by the decider. So the pool has **as many templates as the sequence has steps**.
- **The decider, if there is one, is the last step** and names no player.
- **The picks plus the decider make as many games as `best_of`** (`1`, `2`, `3`, `5`, `7` or `9`). A best-of-3 has two picks and a decider. A league best-of-2 can be two picks and no decider.

**There is no separate game order.** The games are played in the order of the picks, then the decider.

## How a file is checked

1. **The shape**, against `schema.json`: fields that exist, required fields, allowed values.
2. **The rules** that compare things: the templates and towns exist, a pool is part of the tournament's list, the sizes above fit.
3. **The file name** equals the `id`.

Every problem is reported at once, in words, starting with the file name. Typical ones:

| Message | What to do |
|---|---|
| `the file: 'phases' is a required property` | Add the missing field. |
| `phase "Final", best_of: 4 is not one of [1, 2, 3, 5, 7, 9]` | Use one of the allowed values. |
| `templates: unknown template 'Nebula'. Known templates: ...` | Use an id from `data/templates.json`, or add the template there. Ids are case-sensitive. |
| `phase "Groups": the template 'Diamond' is in the pool but not in the tournament's templates (...)` | Add it to the tournament's `templates`. |
| `phase "Final": the pool must have as many templates as the sequence has steps ... (5 templates, 4 steps)` | Add or remove a step, or change the pool. |
| `phase "Final": a best-of-3 needs 3 games, but the sequence gives 1 (0 picks and a decider)` | Fix the picks or the `best_of`. |
| `the file name must match the format id` | Rename the file or change the `id`. |

## Adding a template or a town

Add an entry to [`../data/templates.json`](../data/templates.json) or [`../data/towns.json`](../data/towns.json); see [`../data/README.md`](../data/README.md). A new template needs its `difficulty`, and may state more facts about itself (roads, map size, computer players, where to get it).

## When a rule is unclear

Do not guess. Ask in the pull request, or write it down as an `Open question:` in the spec.
