"""Tests for chat device context preprompt."""

from devices_mcp.chat.device_context import (
    SYSTEM_PREAMBLE,
    merge_device_context_into_messages,
)


def test_merge_device_context_prepends_system():
    messages = [{"role": "user", "content": "What cameras do we have?"}]
    out = merge_device_context_into_messages(messages, "INVENTORY")
    assert out[0]["role"] == "system"
    assert "INVENTORY" in out[0]["content"]
    assert out[1]["content"] == "What cameras do we have?"


def test_merge_device_context_augments_existing_system():
    messages = [
        {"role": "system", "content": "Extra rules"},
        {"role": "user", "content": "Hi"},
    ]
    out = merge_device_context_into_messages(messages, "INVENTORY")
    assert out[0]["role"] == "system"
    assert "INVENTORY" in out[0]["content"]
    assert "Extra rules" in out[0]["content"]


def test_system_preamble_mentions_inventory():
    assert "LIVE HOME INVENTORY" in SYSTEM_PREAMBLE or "inventory" in SYSTEM_PREAMBLE.lower()
