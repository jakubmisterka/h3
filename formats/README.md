# Tournament formats

Each `.json` file here (except `schema.json`) is one **format**: the rules of the pre-game phase for a tournament or a ranked mode. The bot reads these files, so adding a format needs no code change.

## Add a format

1. Copy `el-classico.json` to `formats/<your-id>.json`. The file name must match the `id` inside, for example `my-cup.json` with `"id": "my-cup"`.
2. Edit the copy (fields are explained below).
3. Run the checks from the repository root:

   ```powershell
   poetry run pytest
   ```

   A mistake is reported with the phase and the problem, for example *the pool must be one larger than the number of steps*.
4. Open a pull request.

## Fields

| Field | Meaning |
|---|---|
| `id` | Lowercase words joined by dashes. Same as the file name. |
| `name` | The name players see. |
| `status` | `active` (default) or `archived`. Archived formats stay in the repository but cannot start new matches. Never delete a finished tournament, archive it. |
| `thread_visibility` | `public` (default) or `private`. Who can read the match thread. |
| `phases` | One or more phases, for example group stage and knockout. Players are asked for the phase only if there is more than one. |

Each phase has:

| Field | Meaning |
|---|---|
| `name` | Phase name, unique within the format. |
| `best_of` | `1`, `3` or `5`. |
| `pool` | Template ids from [`data/templates.json`](../data/templates.json). |
| `selection` | How the template is chosen, see below. |
| `trade` | Trade settings. `difficulty` is required, the rest are optional. |
| `allowed_factions` | Optional list of faction ids from [`data/factions.json`](../data/factions.json). Leave it out to allow every faction. |
| `template_overrides` | Optional. Trade settings that differ for one template, keyed by template id. |

### Selection

Bans and picks, in order. **A** is the coinflip winner and **B** the other player:

```json
"selection": {
  "type": "sequence",
  "steps": [
    { "who": "A", "do": "ban" },
    { "who": "B", "do": "ban" },
    { "who": "A", "do": "pick" },
    { "who": "B", "do": "pick" }
  ],
  "game_order": ["pick_1", "pick_2", "decider"]
}
```

- The pool must have exactly **one more template than there are steps**. The template left over is the *decider*.
- The number of picks must be **best-of minus one** (a best-of-3 has 2 picks).
- `game_order` lists the games in the order they are played. `pick_1` is the first pick step, `pick_2` the second, `decider` the leftover template. Every game appears once.

For a mode where players agree on the template themselves (ranked), use `"selection": { "type": "agreed" }` with `best_of` 1. The players name the template when they start the match, and it must be in the pool.

### Trade settings

```json
"trade": { "difficulty": 160, "roll_cost": 500, "rolls_per_player": 1, "max_roll_bans": 2 }
```

| Field | Default | Meaning |
|---|---|---|
| `difficulty` | required | In-game difficulty: `80`, `100`, `130`, `160` or `200`. |
| `roll_cost` | `500` | Gold paid to roll the faction pair. |
| `rolls_per_player` | `1` | Rolls each player may use. |
| `max_roll_bans` | `2` | Factions a player may ban when rolling (0 up to this). |

**Do not write starting gold.** It follows from the difficulty, as in the game: 80% gives 30000, 100% gives 20000, 130% gives 15000, 160% gives 10000 and 200% gives 0. At 200% the game is all-random, so the trade is only a coin toss for color.

Per-template differences go in the phase:

```json
"template_overrides": { "JC": { "difficulty": 130 } }
```

## Add a template or a faction

Add an `{ "id": ..., "name": ... }` entry to [`data/templates.json`](../data/templates.json) or [`data/factions.json`](../data/factions.json). Formats refer to entries by `id`.

## Unclear rules

If a tournament rule is unclear, do not guess. Ask in the pull request, or record it as an `Open question:` in the spec.
