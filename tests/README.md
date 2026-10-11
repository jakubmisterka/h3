# tests

Automatic tests, run with pytest from the repository root:

```powershell
poetry run pytest
```

They never connect to Discord, so they are fast and need no token. They check the plain functions in [`../src/rules/`](../src/rules/). What happens in Discord itself (threads, replies, permissions) is checked by hand in the dev server at the end of each milestone, see the task list in [`../openspec/changes/add-1v1-pregame-flow/tasks.md`](../openspec/changes/add-1v1-pregame-flow/tasks.md).

A test file is named after what it checks: `test_start.py` checks `src/rules/start.py`. Tests import modules from `src/` directly (for example `from rules.start import check_opponent`); this is set by `pythonpath` in [`../pyproject.toml`](../pyproject.toml).
