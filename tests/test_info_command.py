"""Tests the /info command with fake Discord objects, so no connection to Discord is needed."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discord_commands.info import _mode_options, _phase_options, _template_options, info
from rules.formats import parse_format
from rules.info import info_reply
from rules.registry import Registry


@pytest.fixture
def registry(good_format, templates, towns):
    sample = parse_format(good_format, templates, towns)
    old = parse_format(dict(good_format, id="old-cup", name="Old Cup", status="archived"), templates, towns)
    return Registry(towns, templates, {sample.id: sample, old.id: old})


def interaction(registry, mode_typed=None):
    return SimpleNamespace(
        client=SimpleNamespace(registry=registry),
        response=SimpleNamespace(send_message=AsyncMock()),
        namespace=SimpleNamespace(mode=mode_typed),
    )


def run(coroutine):
    return asyncio.run(coroutine)


# --- the command -----------------------------------------------------------------------------


def test_info_for_a_mode_is_sent_privately(registry):
    it = interaction(registry)
    run(info.callback(it, "Sample Cup", None))
    it.response.send_message.assert_awaited_once_with(info_reply(registry, "Sample Cup"), ephemeral=True)


def test_info_for_a_template_is_sent_privately(registry):
    it = interaction(registry)
    run(info.callback(it, "sample-cup", "Jebus Cross"))
    text = it.response.send_message.await_args.args[0]
    assert text.startswith("**Jebus Cross** in Sample Cup")
    assert it.response.send_message.await_args.kwargs == {"ephemeral": True}


def test_an_unknown_mode_is_explained_privately_too(registry):
    it = interaction(registry)
    run(info.callback(it, "nope", None))
    assert "There is no mode called 'nope'" in it.response.send_message.await_args.args[0]
    assert it.response.send_message.await_args.kwargs == {"ephemeral": True}


def test_the_command_is_called_info_and_takes_a_mode_and_an_optional_template():
    assert info.name == "info"
    parameters = {p.name: p.required for p in info.parameters}
    assert parameters == {"mode": True, "template": False, "phase": False}


# --- autocomplete ------------------------------------------------------------------------------


def test_modes_are_offered_by_name_with_the_id_as_value(registry):
    choices = run(_mode_options(interaction(registry), ""))
    assert [(c.name, c.value) for c in choices] == [("Sample Cup", "sample-cup"), ("Old Cup (archived)", "old-cup")]


def test_templates_of_the_chosen_mode_are_offered(registry):
    choices = run(_template_options(interaction(registry, mode_typed="sample-cup"), ""))
    assert [(c.name, c.value) for c in choices] == [("Jebus Cross", "JC"), ("6lm10a", "6lm10a"), ("h3dm1", "h3dm1")]


def test_templates_are_filtered_by_what_is_typed(registry):
    choices = run(_template_options(interaction(registry, mode_typed="Sample Cup"), "jeb"))
    assert [c.value for c in choices] == ["JC"]


def test_no_templates_are_offered_before_a_mode_is_chosen(registry):
    assert run(_template_options(interaction(registry, mode_typed=None), "")) == []


# --- the phase option ------------------------------------------------------------------------------


@pytest.fixture
def two_phase_registry(good_format, templates, towns):
    second = dict(good_format["phases"][0], name="Final")
    good_format["phases"][0]["name"] = "Group"
    good_format["phases"].append(second)
    fmt = parse_format(good_format, templates, towns)
    return Registry(towns, templates, {fmt.id: fmt})


def test_info_can_be_limited_to_one_phase(two_phase_registry):
    it = interaction(two_phase_registry)
    run(info.callback(it, "Sample Cup", None, "Final"))
    text = it.response.send_message.await_args.args[0]
    assert '**Phase "Final"**' in text and "Group" not in text
    assert it.response.send_message.await_args.kwargs == {"ephemeral": True}


def test_the_phases_of_the_chosen_mode_are_offered(two_phase_registry):
    choices = run(_phase_options(interaction(two_phase_registry, mode_typed="sample-cup"), ""))
    assert [(c.name, c.value) for c in choices] == [("Group", "Group"), ("Final", "Final")]


def test_no_phases_are_offered_before_a_mode_is_chosen(two_phase_registry):
    assert run(_phase_options(interaction(two_phase_registry, mode_typed=None), "")) == []


def test_a_mode_with_one_phase_offers_no_phase_choices(registry):
    assert run(_phase_options(interaction(registry, mode_typed="sample-cup"), "")) == []
