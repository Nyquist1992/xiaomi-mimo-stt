"""The Xiaomi MiMo ASR (STT) integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .stats import CallStats

PLATFORMS = ["stt", "sensor"]


@dataclass
class MimoASRRuntimeData:
    """Runtime data attached to the config entry."""

    stats: CallStats


type MimoASRConfigEntry = ConfigEntry[MimoASRRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: MimoASRConfigEntry) -> bool:
    """Set up Xiaomi MiMo ASR from a config entry."""
    entry.runtime_data = MimoASRRuntimeData(stats=CallStats())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MimoASRConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: MimoASRConfigEntry) -> None:
    """Reload the entry when its data (api key / language) changes."""
    await hass.config_entries.async_reload(entry.entry_id)
