"""PreToolUse hook: refuse any tool call that references a .env* secrets file.

.env.example is allowed. Exit code 2 blocks the call and sends stderr to Claude.
Best-effort: it matches file names in path/command arguments, so it can't catch
names assembled at runtime (e.g. `cat .e*`). File *content* being written is not
checked, so docs may mention the file names.
"""
import json
import re
import sys

# ".env", ".env.dev", ".env.prod", ".env*", ".envrc" ... but not ".env.example"
PATTERN = re.compile(r"(?<![\w])\.env(?!\.example(?![\w.-]))", re.IGNORECASE)

# Which tool_input fields name a file, path or command, per tool.
FIELDS = {
    "Bash": ("command",),
    "PowerShell": ("command",),
    "Grep": ("path", "glob"),
    "Glob": ("pattern", "path"),
}
DEFAULT_FIELDS = ("file_path", "path", "notebook_path")


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        tool_input = payload.get("tool_input", {})
        fields = FIELDS.get(payload.get("tool_name"), DEFAULT_FIELDS)
        texts = [str(tool_input[f]) for f in fields if f in tool_input]
    except (json.JSONDecodeError, AttributeError, TypeError):
        texts = [raw]  # fail closed: scan the raw payload instead of ignoring it
    if any(PATTERN.search(t) for t in texts):
        print(
            "Blocked: this project keeps secrets in .env.dev / .env.prod, which "
            "Claude must not read or touch. Use .env.example to see the variable "
            "names, and ask the user to edit the real files.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
