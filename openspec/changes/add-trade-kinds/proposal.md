# Proposal

## Why

The trade the bot runs is one fixed shape: a pair of towns, a town bid, a color bid. Some templates and tournaments trade differently. A mirror template gives both players the same town, so there is nothing to bid on but the color. Sapphire adds two packs of computer-player towns that one player can choose. A tournament that plays "roulette" draws the starting heroes and bids on the right to choose between a hero and a color. Today players run these trades by hand, in the lobby or on a website that is unreliable, which is exactly the lobby time this bot exists to remove.

## What Changes

### What a player sees

A game's trade has a **kind**. The kind decides what the bot draws when the trade starts, what a roll redraws, and which bids follow. Everything else stays: the roll costs gold, bids are reported with `/trade report`, either player may report, undo works, and the thread ends with the lobby settings.

| Kind | Draw | After the roll | Bids |
|---|---|---|---|
| `standard` (today) | a pair of towns | | town, then color |
| `standard` on a **mirror** template | one town, played by both | | color only |
| `standard_with_ai_packs` (Sapphire) | a pair of towns and two packs of 3 computer-player towns, all 8 different | | town, then pack, then color |
| `roulette` | the town(s) as above, then heroes | optional hero bans, the bot draws the heroes | non-mirror: town (each town of the pair comes with its hero), then color. Mirror: one bid, whose winner chooses first either the hero or the color |

1. **Mirror.** The bot draws one town. A roll pays the roll cost and redraws that town, which is banned (a player cannot roll "to the same town"). The only bid is the color; the winner takes the color. The tournament's procedure for banning and choosing the starting hero (who bans how many, who picks first) is not run by the bot; a format can state it in its additional rules.
2. **`standard_with_ai_packs`.** The bot draws the pair and two packs of three computer-player towns, named **pack1** and **pack2**; the pair and the packs are eight different towns. A roll redraws everything, and only the towns of the player pair can be banned; a banned town leaves the player pair but may come up in a pack. After the town bid, the winner of the **pack bid** chooses `pack1` or `pack2` and the other player gets the other pack. Then the color bid.
3. **Roulette.** The bot replaces the website. By default the town(s) are drawn and rolled first. Then, if the trade asks for it, each player in turn (the coinflip winner first) bans heroes of the drawn town(s), up to a number the tournament sets. The bot then draws the heroes: two different heroes of the town for a mirror, one hero of each town of the pair otherwise, never a banned hero and never one the template excludes. The draw is final.
   - Non-mirror: the town bid is the hero bid (naming the town names its hero), then the color bid. The thread shows each town with its hero.
   - Mirror: one bid. Its winner says whether they choose first the **hero** or the **color**; the other player then chooses the other thing. The bot does not record which hero or color is chosen.
   - A tournament can ask for the heroes to be drawn together with the towns, so players see them before deciding to roll; then a roll redraws both, and hero bans are not possible.
4. `/info` says which kind a template is played with in that mode, and the thread's lobby settings end with what the kind decided: the town(s), the packs or the heroes, and who chooses what.

### Choosing the kind (data)

- A new template setting **`trade`**, stacked like the other settings: the template's own default in the catalogue, then the tournament's template list, then the phase's pool. So the same template can be traded as plain mirror in the groups and as roulette in the knockout.
  - `"standard"` (the default when nothing is stated), `"standard_with_ai_packs"`, or an object `{ "kind": "roulette", "hero_bans": 1, "roll_before_heroes": true }` (`hero_bans` is the number of heroes each player may ban, default 0; `roll_before_heroes` defaults to true).
- `mirror` stays a fact of the template. `standard_with_ai_packs` is refused for a mirror template; roulette works for both.
- A new catalogue of **heroes** (`data/heroes.json`): each hero's id, name, town and a link to the community wiki. A template may list `banned_heroes`, the heroes of its towns that its map does not offer (a list of exclusions is shorter than a list of allowed heroes).
- A format file is refused, with a message in plain words, when a kind cannot work: `standard_with_ai_packs` needs at least 8 allowed towns in the phase and no mirror template, `hero_bans` above 0 needs `roll_before_heroes`, a template's `banned_heroes` must be heroes in the catalogue, and a roulette needs enough heroes left to draw.

### Assumptions

- The tournament text this is based on (rules in Polish for a mirror roulette) has the coinflip winner (player A) act first in the hero bans, as in all the other steps.
- In `standard_with_ai_packs` the colors work as in the standard trade (red moves first).
- 200% (color toss) games stay as they are: the bot says their trade is not available.

## Out of scope

- Tracking which hero or color a player finally takes after a roulette bid, or enforcing any hero ban/pick procedure that the bot does not run.
- Checking the lobby, running a clock, or drawing heroes for any other purpose than the roulette.
- The trade of 200% games (color toss only); a separate follow-up change.
- Filling the hero catalogue with every hero of the game as a promise of completeness: the catalogue is data that maintainers extend, like towns and templates.

## Capabilities

### New Capabilities

- `hero-roulette`: the hero catalogue and the heroes a template's map does not offer; the roulette trade (hero bans, the bot's draw of the heroes, `roll_before_heroes`, the two kinds of bid) and undo of its steps.

### Modified Capabilities

- `game-trade`: a trade has a kind; the mirror trade and the trade with computer-player packs; the sections, the draw, the roll and the lobby settings depend on the kind.
- `tournament-formats`: the `trade` setting and its stacking; the checks that a kind can work.
- `mode-info`: the template reply says how the trade is run in that mode.

## Impact

- `data/heroes.json` (new, with a README entry) and `data/templates.json` (optional `trade`, `banned_heroes`); loading and checks in `src/rules/catalogue.py` and `src/rules/registry.py`.
- `formats/schema.json`, `src/rules/formats.py`, `src/rules/template_settings.py`: the `trade` setting, its checks and its stacking.
- `src/rules/trade.py` (the trade and its sections become data-driven by kind), a new module for the draws (pack and hero draws), `src/state.py` (new record types, and records that no longer assume a pair of two towns), `src/rules/situation.py` and `src/rules/undo.py` (what comes next after each step, status, undo).
- `src/discord_commands/trade.py`: the report's choices per section, a command for hero bans, and autocomplete for them.
- Tests for each rule above; `data/README.md` and `formats/README.md`. No new dependency.
