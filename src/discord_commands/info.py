"""The /info command: how a mode works, and how a template is played in it."""

import discord
from discord import app_commands

from rules.info import info_reply, mode_choices, phase_choices, template_choices


@app_commands.command(name="info", description="Show how a tournament mode works, or how a template is played in it")
@app_commands.describe(
    mode="The tournament mode",
    template="A template of that mode (leave out to see the whole mode)",
    phase="Only this phase of the mode (leave out to see all phases)",
)
async def info(
    interaction: discord.Interaction, mode: str, template: str | None = None, phase: str | None = None
) -> None:
    # Nothing here is a secret, but it would only clutter the channel: only the asker sees the reply.
    reply = info_reply(interaction.client.registry, mode, template, phase)
    await interaction.response.send_message(reply, ephemeral=True)


@info.autocomplete("mode")
async def _mode_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    choices = mode_choices(interaction.client.registry, current)
    return [app_commands.Choice(name=name, value=value) for name, value in choices]


@info.autocomplete("template")
async def _template_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    mode = interaction.namespace.mode or ""  # what the player has already chosen for `mode`
    choices = template_choices(interaction.client.registry, mode, current)
    return [app_commands.Choice(name=name, value=value) for name, value in choices]


@info.autocomplete("phase")
async def _phase_options(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    mode = interaction.namespace.mode or ""
    choices = phase_choices(interaction.client.registry, mode, current)
    return [app_commands.Choice(name=name, value=value) for name, value in choices]
