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
| `trade` | How a game on this template is traded by default: `standard`, `standard_with_ai_packs`, a roulette or `roulette_with_ai_packs`. A tournament can choose another for a template, see [`../formats/README.md`](../formats/README.md#how-a-game-is-traded). The kinds with packs cannot be used on a mirror template. |
| `banned_heroes` | The heroes the template's map does not offer, as a list of ids or names from `heroes.json`. A roulette never draws them. |
| `allowed_heroes` | The heroes banned by default (see [Heroes](#heroes)) that the template's map enables, for example the campaign heroes a map turns on. A hero cannot be both banned and allowed. |
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

## Heroes

`heroes.json` lists the heroes a roulette trade draws from (see [`../formats/README.md`](../formats/README.md)). The file is optional: a repository without it only cannot use a roulette. Each hero has:

| Field | What it says |
|---|---|
| `id` | A short lowercase id (`orrin`, `lord_haart`), the name of the hero's page on the wiki. |
| `name` | The name players read and type (`Orrin`). No two heroes share a name. |
| `town` | The id of the hero's town, from `towns.json`. |
| `link` | The hero's page on the community wiki, starting with `https://`. |
| `campaign_hero` | `true` for a hero who comes with a campaign (Gelu, Boragus, ...), `false` for every other hero. It only says what the hero is: campaign heroes are also `banned_by_default`. |
| `banned_by_default` | `true` for the heroes that are not offered unless a template allows them: the campaign heroes, the three more that HotA bans in every template pack (Galthran, Sir Mullich, Thorgrim), and the eight that its template editor bans depending on the water of the map (Sylvia, Voy, Elmore, Haugir, Beatrice, Kinkeria, Derek, Biarma; nobody plays with water, so a template that has water allows them). |
| `banned_on_mirrors` | `true` for the heroes that are not offered on a mirror template. Left out: `false`. |

```json
{ "id": "orrin", "name": "Orrin", "town": "castle", "link": "https://heroes.thelazy.net/index.php/Orrin", "campaign_hero": false, "banned_by_default": false }
```

The file was made from the heroes table of <https://heroes.thelazy.net/index.php/List_of_heroes>, the town of a hero following from the hero's class, and from the campaign heroes that are "fully available in Map Editor" on <https://heroes.thelazy.net/index.php/List_of_campaign_heroes>. The default bans are those of the template editor of HotA (<https://h3hota.com/en/template-format>, section Heroes), and the heroes banned on mirror templates.

**A template may not offer all the heroes.** A hero banned by default (or, on a mirror template, banned on mirrors) is not offered, and a template's own lists win over the defaults:

- **`allowed_heroes`** in `templates.json` lifts the default ban of the heroes it lists (ids or names). A hero that is not banned by default needs no permission, so listing one is a mistake.
- **`banned_heroes`** bans more heroes (ids or names). A hero cannot be in both lists.

The bot never draws a hero the template's map does not offer.

```json
{ "id": "6lm10a", "name": "6lm10a", "difficulty": 160, "allowed_heroes": ["Gelu", "Sylvia"], "banned_heroes": ["Orrin"] }
```

The necropolis death knight whom the wiki names "Lord Haart" is listed as "Haart Lich", so that the two Haarts can be told apart.

## What is checked

The bot, and the tests (`poetry run pytest`), reject a file that breaks these rules, and say which entry is wrong: a missing or extra field, an empty `id` or `name`, an id used twice, or a `difficulty` that is not one of the supported values.
