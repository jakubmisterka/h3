from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_packages_import():
    import commands  # noqa: F401
    import rules  # noqa: F401


def test_data_directories_exist():
    assert (ROOT / "formats").is_dir()
    assert (ROOT / "data").is_dir()
