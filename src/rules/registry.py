"""Everything the bot reads from the repository when it starts: the towns, the templates and the formats.

`load_registry` either returns all of it, checked, or raises one `RegistryError` that lists every
problem found in every file, so a contributor can fix them all in one go.
"""

from dataclasses import dataclass
from pathlib import Path

from rules.catalogue import Catalogue, CatalogueError, load_templates, load_towns
from rules.formats import Format, FormatError, load_formats


class RegistryError(ValueError):
    """Some data file is not valid. `problems` lists each problem, in words, starting with the file name."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


class ModeError(ValueError):
    """A mode cannot be used for a new match. The message is shown to the player."""


def _count(number: int, word: str) -> str:
    return f"{number} {word}" if number == 1 else f"{number} {word}s"


@dataclass(frozen=True)
class Registry:
    towns: Catalogue
    templates: Catalogue
    formats: dict[str, Format]  # by format id

    def modes_for_new_matches(self) -> list[Format]:
        """The modes a match can be started in: active formats only. Archived ones stay on record, hidden."""
        return [fmt for fmt in self.formats.values() if fmt.active]

    def find_format(self, text: str) -> Format | None:
        """A format by id or name, ignoring letter case, whatever its status (archived ones can be looked up)."""
        wanted = text.strip().lower()
        return next((f for f in self.formats.values() if wanted in (f.id.lower(), f.name.lower())), None)

    def choose_mode(self, text: str) -> Format:
        """The mode a player named for a new match. Raises ModeError, in words, if it cannot be used."""
        fmt = self.find_format(text)
        if fmt is None:
            names = ", ".join(f.name for f in self.modes_for_new_matches())
            available = f"Available modes: {names}." if names else "There are no modes available."
            raise ModeError(f"There is no mode called {text!r}. {available}")
        if not fmt.active:
            raise ModeError(f"{fmt.name} is archived and cannot start new matches.")
        return fmt

    def summary(self) -> str:
        """One line saying what was loaded, for the log: counts, and the formats by id."""
        formats = ", ".join(fmt.id + ("" if fmt.active else " (archived)") for fmt in self.formats.values())
        return (
            f"{_count(len(self.towns.entries), 'town')}, {_count(len(self.templates.entries), 'template')}, "
            f"{_count(len(self.formats), 'format')} ({formats or 'none'})"
        )


def load_registry(root: Path) -> Registry:
    """Load and check `data/` and `formats/` under `root`."""
    problems = []
    towns = templates = None
    try:
        towns = load_towns(root / "data" / "towns.json")
    except CatalogueError as e:
        problems.append(str(e))
    try:
        templates = load_templates(root / "data" / "templates.json")
    except CatalogueError as e:
        problems.append(str(e))
    if problems:
        raise RegistryError(problems)  # formats cannot be checked without the lists they refer to

    try:
        formats = load_formats(root / "formats", templates, towns)
    except FormatError as e:
        raise RegistryError(e.errors) from e
    return Registry(towns, templates, formats)
