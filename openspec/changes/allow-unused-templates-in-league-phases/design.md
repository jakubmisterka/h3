# Design

## Context

`formats._sequence_problems` refuses a sequence phase whose pool is not exactly as large as its sequence, because every template is banned, picked, or taken by the decider. The bot's selection code already copes with leftovers: it ends when the steps are done, and the games are the picks (plus the decider's template when there is one).

## Decisions

**Relax the check only without a decider.** The decider takes "the one template that is left", so with a decider the pool must still match the steps exactly. Without one, nothing consumes the leftovers, so the pool only needs a template for every step (at least as many as the steps). A smaller pool stays refused.

**No change in the match.** The "Remaining" list the bot shows during the selection simply lists more templates for longer, and the leftovers are never played.

## Risks / Trade-offs

- A typo that adds an extra template to a phase with no decider is no longer caught by this check. The best-of and picks check still catches wrong game counts.
