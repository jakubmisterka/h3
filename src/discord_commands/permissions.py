"""The Discord permissions the bot needs for each thing it does, and a check that names what is missing.

A server admin can take any of these away from the bot, in a single channel or everywhere.
Checking first lets the bot say exactly what to give back, instead of failing half way
(for example after posting an announcement but before creating its thread).
"""

LABELS = {
    "view_channel": "View Channel",
    "send_messages": "Send Messages",
    "create_public_threads": "Create Public Threads",
    "create_private_threads": "Create Private Threads",
    "send_messages_in_threads": "Send Messages in Threads",
}

# Attribute names of discord.Permissions that each action needs.
PUBLIC_THREAD = ("view_channel", "send_messages", "create_public_threads", "send_messages_in_threads")
PRIVATE_THREAD = ("view_channel", "create_private_threads", "send_messages_in_threads")


def missing(permissions, needed: tuple[str, ...]) -> list[str]:
    """The labels of the needed permissions that `permissions` does not have.

    `permissions` is a discord.Permissions (anything with those attributes works).
    """
    return [LABELS[name] for name in needed if not getattr(permissions, name)]


def missing_message(labels: list[str]) -> str:
    """The text shown to the player when the bot lacks permissions."""
    return (
        "I can't do that in this channel: I am missing the permission "
        + ", ".join(f"**{label}**" for label in labels)
        + ". Ask a server admin to allow it for me here."
    )
