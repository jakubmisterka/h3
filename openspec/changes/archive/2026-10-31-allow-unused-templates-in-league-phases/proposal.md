# Proposal: a league phase can leave templates unused

## Why

In the Liga Heroes, a match of two games is played as ban, ban, pick, pick over a pool of several templates (seven in some divisions). The templates that were neither banned nor picked are simply not played. Today a sequence phase must use every template of its pool (each one is banned, picked or taken by the decider), so a two-game phase with a pool of seven templates is refused. League tournaments with larger pools cannot be added.

## What the players see

Nothing changes for a phase that has a decider, or whose pool is as large as its sequence. In a phase with no decider and a pool larger than its sequence, the players ban and pick as the sequence says. After the last step the games are the picks, and the remaining templates are not played. The thread's "Remaining" list shows them as long as the steps go on.

## What changes

- Validation: a sequence phase with no decider may have a pool that is larger than its sequence. A phase with a decider still needs exactly as many templates as steps, since the decider takes the one template that is left.
- Docs: `formats/README.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-formats`: the validation of the pool against the sequence.

## Out of scope

- A pool smaller than the sequence is still refused.
- Templates left over in a phase with a decider.

## Impact

`src/rules/formats.py` (the validation), `formats/README.md`, and tests.
