## ADDED Requirements

### Requirement: A template and a tournament choose how a game is traded
The template catalogue and the format file SHALL be able to state a `trade` setting for a template, which chooses the kind of the game's trade: `standard`, `standard_with_ai_packs`, or a roulette written as an object with `kind` `roulette`, `hero_bans` (0 to 3 heroes each player may ban, default 0) and `roll_before_heroes` (default true). It SHALL stack like the other settings: the template's own value in the catalogue, then the one written for the template in the tournament's list, then the one written for it in a phase's pool, the most specific replacing the one before. A template that states nothing, in a tournament that states nothing, SHALL be traded as `standard`. The `trade` setting SHALL NOT be written for the whole tournament.

#### Scenario: A template states its kind
- **WHEN** the catalogue gives Sapphire the trade `standard_with_ai_packs` and no format changes it
- **THEN** Sapphire is traded with computer-player packs in every phase

#### Scenario: A tournament changes the kind in one phase
- **WHEN** the tournament's list gives a template no trade and the pool of the final gives it a roulette with 1 hero ban
- **THEN** the template has a standard trade in the other phases and a roulette in the final

#### Scenario: Defaults of a roulette
- **WHEN** a format writes the trade of a template as `{ "kind": "roulette" }`
- **THEN** it has no hero bans and the heroes are drawn after the rolls

#### Scenario: Nothing stated
- **WHEN** neither the catalogue nor the format states a trade for a template
- **THEN** the trade is the standard one

#### Scenario: A kind that does not exist
- **WHEN** a format writes a trade kind that is not one of the kinds
- **THEN** validation fails and lists the kinds

#### Scenario: For the whole tournament
- **WHEN** a format writes a trade in the tournament's own settings
- **THEN** validation fails and says it can only be chosen for a template

### Requirement: A format is refused when its trade cannot work
Validation SHALL refuse a trade setting that cannot work, and say why: the trade with computer-player packs for a mirror template, or in a phase that allows fewer than eight towns; hero bans together with `roll_before_heroes` false; a roulette in a phase where an allowed town would have too few heroes left for the draw after the template's banned heroes and the most bans players could make; a roulette when the hero catalogue is empty.

#### Scenario: Packs on a mirror
- **WHEN** a format gives a mirror template the trade `standard_with_ai_packs`
- **THEN** validation fails and says a mirror template cannot have packs

#### Scenario: Too few towns
- **WHEN** a phase allows seven towns and a template in its pool has packs
- **THEN** validation fails and says packs need eight allowed towns

#### Scenario: Hero bans without the rolls first
- **WHEN** a roulette has `hero_bans` 1 and `roll_before_heroes` false
- **THEN** validation fails and says the heroes cannot be banned before they are drawn

#### Scenario: Too few heroes
- **WHEN** a roulette allows a town whose heroes, after the template's banned heroes and the bans players could make, are fewer than the heroes to draw
- **THEN** validation fails and names the town and the template
