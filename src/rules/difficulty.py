"""What a template's difficulty means: the gold each player starts with, and which trade steps the game has.

Difficulty is the in-game difficulty in percent. It belongs to the template (`data/templates.json`),
because that is how the template is played.
"""

# Gold each human player starts with at each difficulty. Source: https://heroes.thelazy.net/index.php/Difficulty
DIFFICULTY_GOLD = {80: 30000, 100: 20000, 130: 15000, 160: 10000, 200: 0}

# At 200% the lobby is all-random and nobody has gold, so there is nothing to roll or bid for.
ALL_RANDOM_DIFFICULTY = 200

TRADE_SECTIONS = ("town_roll", "town_bid", "color_bid")
ALL_RANDOM_SECTIONS = ("color_toss",)


def supported_difficulties() -> str:
    """The supported difficulties in words, for messages."""
    return ", ".join(f"{difficulty}%" for difficulty in DIFFICULTY_GOLD)


def starting_gold(difficulty: int) -> int:
    """The gold each player starts with at this difficulty."""
    if difficulty not in DIFFICULTY_GOLD:
        raise ValueError(f"difficulty {difficulty} is not supported (use one of {supported_difficulties()})")
    return DIFFICULTY_GOLD[difficulty]


def default_sections(difficulty: int) -> tuple[str, ...]:
    """The steps of a game's trade at this difficulty, in order."""
    starting_gold(difficulty)  # refuses an unsupported difficulty
    return ALL_RANDOM_SECTIONS if difficulty == ALL_RANDOM_DIFFICULTY else TRADE_SECTIONS
