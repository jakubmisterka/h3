from types import SimpleNamespace

from discord_commands.permissions import PRIVATE_THREAD, PUBLIC_THREAD, missing, missing_message


def perms(**given):
    """A stand-in for discord.Permissions where everything is allowed except what is given as False."""
    everything = dict.fromkeys(
        [
            "view_channel",
            "send_messages",
            "create_public_threads",
            "create_private_threads",
            "send_messages_in_threads",
            "read_message_history",
        ],
        True,
    )
    return SimpleNamespace(**{**everything, **given})


def test_nothing_is_missing_when_everything_is_allowed():
    assert missing(perms(), PUBLIC_THREAD) == []
    assert missing(perms(), PRIVATE_THREAD) == []


def test_missing_permission_is_named_with_its_discord_label():
    assert missing(perms(create_public_threads=False), PUBLIC_THREAD) == ["Create Public Threads"]


def test_every_missing_permission_is_listed():
    found = missing(perms(create_public_threads=False, send_messages_in_threads=False), PUBLIC_THREAD)
    assert found == ["Create Public Threads", "Send Messages in Threads"]


def test_public_and_private_threads_need_different_permissions():
    # Revoking Create Public Threads must not stop private threads, and the other way round.
    assert missing(perms(create_public_threads=False), PRIVATE_THREAD) == []
    assert missing(perms(create_private_threads=False), PUBLIC_THREAD) == []
    assert missing(perms(create_private_threads=False), PRIVATE_THREAD) == ["Create Private Threads"]


def test_reading_records_back_needs_message_history():
    # Without it the bot could create the thread but not read the match records back.
    assert missing(perms(read_message_history=False), PRIVATE_THREAD) == ["Read Message History"]
    assert missing(perms(read_message_history=False), PUBLIC_THREAD) == ["Read Message History"]


def test_message_names_the_permissions():
    text = missing_message(["Create Public Threads", "Send Messages in Threads"])
    assert "**Create Public Threads**" in text and "**Send Messages in Threads**" in text
