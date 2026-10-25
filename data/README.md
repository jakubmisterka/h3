# data

The lists that the rest of the bot refers to. They are plain JSON files, so adding an entry needs no code change.

| File | What it lists |
|---|---|
| `towns.json` | The towns players can get. Source: the town list on the [community wiki](https://heroes.thelazy.net/index.php/Town). |
| `templates.json` | The templates tournaments can use, by the name players know them by, each with the difficulty it is played on. |

Every entry in both files has an `id` and a `name`:

```json
{ "id": "castle", "name": "Castle" }
```

- `id`: what other files (the tournament formats in [`../formats/`](../formats/)) and the bot's commands refer to. It must be unique in its file.
- `name`: what players read. Players may type either the id or the name, in any letter case.

For many entries the id is just the name in lower case, so the two look redundant. They are kept apart on purpose: the id is a short, stable key, and the name is what the game shows. For example the template `JC` is called *Jebus Cross* in the game: formats say `JC`, players read Jebus Cross, and typing either finds it. A display name can also be reworded later without editing every tournament format that uses the entry.

Neither may be empty. Keep ids to the names players actually use: for templates that is the template's own name (`JC`, `6lm10a`), for towns a lowercase word.

## Templates also state their difficulty

```json
{ "id": "JC", "name": "Jebus Cross", "difficulty": 160 }
```

`difficulty` is the in-game difficulty in percent that the template is played on, and it must be one of 80, 100, 130, 160 or 200. It belongs to the template, not to a tournament: it decides how much gold each player starts with, and at 200% the game is all-random and only the color is tossed. Towns have no `difficulty`.

| Difficulty | Starting gold for each player |
|---|---|
| 80% | 30000 |
| 100% | 20000 |
| 130% | 15000 |
| 160% | 10000 |
| 200% | 0 |

## Other facts a template can state

All of these are optional. **A fact that is not stated is unknown, and the bot says nothing about it**: it never guesses, and a template with none of them works as it always did. Fill in only what you know.

| Field | What it says |
|---|---|
| `roads`, `map_size`, `ai` | What is played, each as a `default` and a list of `allowed` values (see below). A tournament may choose another of the allowed values for its templates; if it chooses nothing, the default is played. |
| `sim_turns` | How long simultaneous turns are recommended to last: the last day, as month, week and day in digits. `117` is month 1, week 1, day 7, and `121` is month 1, week 2, day 1. The day is the last digit (1 to 7), the week the digit before it (1 to 4), and the month the digits before that (`1214` is month 12, week 1, day 4). A tournament may choose another date. |
| `mirror` | `true` when both players play the same town. A mirror template is always played with underground, so every map size it states ends in `+U`. |
| `built_in` | `true` when the template comes with HotA. |
| `download` | A link starting with `https://` where the template can be downloaded. State `built_in` or `download`, never both. |
| `description` | What the template is, as free text for `/info`. |
| `additional_rules` | Additional rules the template's maker set, for example how the computer players are picked. Shown by `/info`, and posted in the match thread when the trade of a game on the template starts. A tournament may replace them for the template, see [`../formats/README.md`](../formats/README.md). |

`description` and `additional_rules` are free text of 1 to 1000 characters. The bot only shows them, it does not check that players follow them.

The shape of `roads`, `map_size` and `ai` is the same, a default and what is allowed. The default must be one of the allowed values.

- **Roads**: `none`, or `slow`, `mid` and `fast` (the game's dirt, gravel and cobblestone roads) joined by `+` in that order, for example `mid` or `slow+mid`. Players seldom use more than one road type, but the lobby allows it.
- **Map size**: `S`, `M`, `L`, `XL`, `H`, `XH` or `G`, followed by `+U` when it is played with underground, for example `L+U`.
- **Computer players** (`ai`): a number from 0 to 6, because a game has at most 8 players and two of them are the humans.

<!-- templates example -->
```json
[
  {
    "id": "JC",
    "name": "Jebus Cross",
    "difficulty": 160,
    "roads": { "default": "mid", "allowed": ["none", "slow", "mid", "fast"] },
    "map_size": { "default": "L+U", "allowed": ["L", "L+U", "XL+U"] },
    "ai": { "default": 0, "allowed": [0, 3, 6] },
    "sim_turns": "117",
    "download": "https://example.com/jebus-cross",
    "description": "Four islands around a central town",
    "additional_rules": "The computer players are picked alternately, blue first"
  },
  { "id": "6lm10a", "name": "6lm10a", "difficulty": 160, "built_in": true },
  {
    "id": "h3dm1",
    "name": "h3dm1",
    "difficulty": 160,
    "mirror": true,
    "map_size": { "default": "L+U", "allowed": ["L+U", "XL+U"] }
  }
]
```

The links in this example are made up. **The timer is not here.** A timer belongs to a tournament, not to a template, so it is written in the tournament's format file; see [`../formats/README.md`](../formats/README.md).

## What is checked

The bot, and the tests (`poetry run pytest`), reject a file that breaks these rules, and say which entry is wrong: a missing or extra field, an empty `id` or `name`, an id used twice, or a `difficulty` that is not one of the supported values.
