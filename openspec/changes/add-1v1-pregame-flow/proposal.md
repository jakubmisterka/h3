# Proposal

## Why

HotA tournament games last 6h+, yet players still spend lobby time on the same ritual before every game: coinflip, template bans and picks, then bidding for factions and color. None of it needs the game. The bot currently only answers `/hello`. This change moves the whole 1v1 pre-game phase into Discord, so players enter the lobby, read off the settings and start.

## What Changes

### What a player sees

1. In any channel the bot can see, a player runs `/match start` and names the **mode** (a tournament format, or a ranked game) and the **opponent**. If the mode has several phases (group stage, early knockout, late knockout), the bot also asks which one. If the mode lets players agree on the template themselves (ranked), the player gives the template.
2. The bot opens a **thread** for the match and flips the coinflip itself. It announces the winner (called **A**; the other player is **B**). A bans first and bids first.
3. In the thread, players run `/ban` and `/pick` in the order the mode prescribes, with autocomplete of the remaining templates. The bot announces whose turn it is and rejects commands from the wrong player. When the sequence ends, the bot announces the games in play order with their templates.
4. For each game, the bot walks the players through the **trade** one section at a time. First the bot draws a random pair of factions and announces it with the roll cost and who may roll; each eligible player rolls (banning 0-2 factions, and the bot draws a new pair) or skips, and bidding without a word counts as skipping. Then players bid between themselves in the thread for the faction choice and for color, and either player reports each result (winner, amount, choice). The bot keeps the running gold and can undo the last player report; its own random draws are final. Players set the final factions in the lobby by hand.
5. When the trade of a game is complete, the bot posts the **lobby settings**: template, factions, colors and starting gold for each player.
6. Players may stop at any point, for example after the first game's trade, and continue later by reopening the thread. The bot rebuilds the match from the thread's own messages.

### Behind that flow

- Tournament formats become JSON rule-set files in the repo, validated automatically, so contributors can add formats by pull request.
- Match state lives in the bot's own thread messages. There is no database.
- Slash commands only; no privileged Message Content intent.
- The `/hello` command is removed. It only proved that the Discord integration works, and the real commands replace it.

### Out of scope

- Any h3.gg integration, including checking that the players are entered in the tournament. The bot trusts the command.
- A database or any storage outside the thread.
- Bidding done inside the bot (buttons, modals). Players bid in the thread; the bot only records results.
- Formats other than 1v1, and BO5 specifics beyond what the generic sequence already supports.
- Template-specific trade rules that add or remove sections. The section list is data, but no template needs a different one yet.
- Tournament results, brackets and match reporting after the game.
- Timers and reminders for slow players.
- A per-server setting for which channel matches may start in. The match starts, and its thread is created, in the channel where the command is run. A server that wants a dedicated channel limits the bot's access to it through Discord permissions.

### Follow-up ideas (not part of this change)

- **Rewind with consent:** a `/rewind` command with autocomplete of recent steps, so a player can ask to go back to an earlier step (for example after a mistaken ban or pick), and the opponent must accept. It would be one more event in the thread, so nothing is deleted. It must not go back past a random draw (a roll, a toss), to prevent rerolling for a better result. It could also resume an archived thread. A right-click "Rewind to here" message command was considered and can be added later.

## Capabilities

### New Capabilities

- `tournament-formats`: the JSON rule-set files: phases, template pools, best-of, ban/pick sequence or agreed templates, game order, trade rules with per-template overrides, thread visibility; plus the validation contributors' files must pass.
- `match-setup`: starting a match, choosing mode and phase, the coinflip, the match thread, and resuming a match from the thread after a restart or reopened thread.
- `template-selection`: the ban/pick sequence that turns the template pool into the ordered list of games, with turn enforcement.
- `game-trade`: the per-game trade (roll, faction bid, color bid), the gold ledger, undo, and the final lobby settings.

### Modified Capabilities

None. There are no existing specs.

## Impact

- **Code:** new modules under `src/` for rule-set loading and validation, the selection sequence, the trade ledger, and thread-state encoding; thin Discord handlers in `src/bot.py` (or modules it registers). Rule logic stays in plain functions.
- **Data:** a new `data/factions.json` catalogue of the 12 towns, a `data/templates.json` catalogue starting with JC, 6lm10a and h3dm1, and a new `formats/` directory with the JSON rule-sets and their schema, starting with the El Classico format (BO1, ban, ban). Other formats, such as ranked and the multi-phase h3.gg knockouts, come later, once their templates and settings are known.
- **Dependencies:** a JSON-schema validator and `pytest` as a dev dependency (via `poetry add`).
- **Existing code:** `/hello` is deleted from `src/bot.py` (**BREAKING** for anyone using it, but it was only a smoke test). The syntax error at `src/bot.py:31` (`def main() ->  :`) must be fixed, since the bot cannot start with it. `CLAUDE.md` is updated, because it describes the bot as a single `/hello` command.
- **Discord setup:** the bot needs permission to create threads, send messages in threads and read message history, in the dev and prod applications. No new intents.
