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

`difficulty` is the in-game difficulty in percent that the template is played on. It belongs to the template, not to a tournament: it decides how much gold each player starts with (130% gives 15000, 160% gives 10000, and so on), and at 200% the game is all-random and only the color is tossed. Towns have no `difficulty`.

More facts about a template (a timer, where to download it) are expected to be added here later, as extra fields.

## What is checked

The bot, and the tests (`poetry run pytest`), reject a file that breaks these rules, and say which entry is wrong: a missing or extra field, an empty `id` or `name`, an id used twice, or a `difficulty` that is not a whole number.
