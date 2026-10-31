# obrazy (screenshots)

The screenshots of [`../instrukcja.md`](../instrukcja.md). The guide has each one as a commented-out line, so it reads well without them. When you add a file, uncomment its line in the guide (`<!-- ![...](obrazy/...) -->` becomes `![...](obrazy/...)`).

Take them in the dev server, in a match thread between two test accounts. A PNG of the thread, about 900 px wide, with no tokens or private names visible.

| File | What to show | How to get it |
|---|---|---|
| `01-start-meczu.png` | The thread right after the start: the record of the match, the rules, the coinflip and the first step | `/match start` in mode `mp2026`, phase `Group phase` |
| `02-otwarcie-handlu.png` | The opening of a trade with "Next step: town roll" | after the bans, `/trade start` |
| `03-ruletka-bohaterow.png` | The heroes drawn by the bot and the bid for the first choice | `/match start` in mode `king-of-h3dm2`, phase `From 1/8 finals`, skip the rolls and send `/trade ban-heroes` twice |
| `04-ustawienia-lobby.png` | The lobby settings after the last bid, with the red player first | finish a trade with `/trade report` |

Optional extras, if you want a richer guide: the autocomplete of `/ban` (the list of remaining templates), the reply of `/info mode:mp2026`, and the thread of `/match undo` with the agreement.
