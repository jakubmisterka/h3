"""Everything the bot reads from the repository at start-up: catalogues and formats."""

from dataclasses import dataclass
from pathlib import Path

from rules.catalogue import Catalogue, load_catalogue
from rules.formats import Format, load_formats


@dataclass(frozen=True)
class Registry:
    factions: Catalogue
    templates: Catalogue
    formats: dict[str, Format]

    def find_format(self, text: str) -> Format | None:
        """Find a format by id or name, ignoring case."""
        wanted = text.strip().lower()
        return next((f for f in self.formats.values() if wanted in (f.id.lower(), f.name.lower())), None)


def load_registry(root: Path) -> Registry:
    """Load and validate data/ and formats/ under `root`. Raises if any file is invalid."""
    factions = load_catalogue(root / "data" / "factions.json")
    templates = load_catalogue(root / "data" / "templates.json")
    formats = load_formats(root / "formats", templates, factions)
    return Registry(factions, templates, formats)
