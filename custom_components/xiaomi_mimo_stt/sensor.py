"""Diagnostic sensors for Xiaomi MiMo ASR.

Modelled on hass-cortex/xiaomi-mimo-tts sensor design, adapted for STT:
 - last_transcript is the killer feature for accuracy diagnosis
 - token / daily-usage / cost sensors (billing is ¥0.5 per audio hour)
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MimoASRConfigEntry
from .stats import CallStats

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

ICONS = {
    "requests_total": "mdi:counter",
    "requests_success": "mdi:check-circle",
    "requests_failed": "mdi:alert-circle",
    "last_transcript": "mdi:text-recognition",
    "last_duration": "mdi:timer-outline",
    "average_duration": "mdi:chart-line",
    "requests_today": "mdi:calendar-today",
    "tokens_today": "mdi:ticket-percent-outline",
    "tokens_total": "mdi:ticket-confirmation-outline",
    "tokens_last": "mdi:ticket-outline",
    "cost_today": "mdi:cash",
    "audio_today": "mdi:waveform",
    "last_error": "mdi:bug-outline",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MimoASRConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MiMo ASR diagnostic sensors."""
    stats: CallStats = config_entry.runtime_data.stats
    device = DeviceInfo(
        identifiers={("xiaomi_mimo_stt", config_entry.entry_id)},
        name=config_entry.data.get("name", "Xiaomi MiMo ASR"),
        manufacturer="Xiaomi",
        model="MiMo-V2.5-ASR",
        entry_type=DeviceEntryType.SERVICE,
    )
    entities: list[SensorEntity] = [
        MimoCounterSensor(stats, device, "requests_total", "Requests total", SensorStateClass.TOTAL_INCREASING, entry_id=config_entry.entry_id),
        MimoCounterSensor(stats, device, "requests_success", "Requests success", SensorStateClass.TOTAL_INCREASING, enabled_default=False, entry_id=config_entry.entry_id),
        MimoCounterSensor(stats, device, "requests_failed", "Requests failed", SensorStateClass.TOTAL_INCREASING, entry_id=config_entry.entry_id),
        MimoTranscriptSensor(stats, device, entry_id=config_entry.entry_id),
        MimoDurationSensor(stats, device, "last_duration", "Last duration", restore=True, entry_id=config_entry.entry_id),
        MimoDurationSensor(stats, device, "average_duration", "Average duration", restore=False, entry_id=config_entry.entry_id),
        MimoCounterSensor(stats, device, "requests_today", "Requests today", SensorStateClass.TOTAL, entry_id=config_entry.entry_id),
        MimoTokenSensor(stats, device, "tokens_today", "Tokens today", entry_id=config_entry.entry_id),
        MimoTokenSensor(stats, device, "tokens_total", "Tokens total", entry_id=config_entry.entry_id),
        MimoTokenSensor(stats, device, "tokens_last", "Tokens last request", enabled_default=False, entry_id=config_entry.entry_id),
        MimoCostSensor(stats, device, entry_id=config_entry.entry_id),
        MimoAudioSensor(stats, device, entry_id=config_entry.entry_id),
        MimoErrorSensor(stats, device, entry_id=config_entry.entry_id),
    ]
    async_add_entities(entities)


class _MimoSensorBase(SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, stats: CallStats, device: DeviceInfo, key: str, name: str, entry_id: str | None = None) -> None:
        self._stats = stats
        self._key = key
        self._attr_name = name
        self._attr_icon = ICONS.get(key)
        self._attr_device_info = device
        if entry_id:
            # Without unique_id entities never register in the entity registry:
            # they are invisible on the device page and get random entity_ids.
            self._attr_unique_id = f"{entry_id}_{key}"

    @property
    def _suffix(self) -> str:
        return self._key.replace("_", " ").title()

    async def async_added_to_hass(self) -> None:
        self._stats.add_listener(self.async_write_ha_state)


class MimoCounterSensor(_MimoSensorBase):
    """Monotonic counters fed straight from CallStats fields."""

    def __init__(self, stats: CallStats, device: DeviceInfo, key: str, name: str, state_class: SensorStateClass, enabled_default: bool = True, entry_id: str | None = None) -> None:
        super().__init__(stats, device, key, name, entry_id=entry_id)
        self._attr_state_class = state_class
        self._attr_entity_registry_enabled_default = enabled_default

    @property
    def native_value(self) -> int | None:
        value = getattr(self._stats, self._key)
        return int(value) if value is not None else (0 if self._attr_state_class == SensorStateClass.TOTAL_INCREASING else None)


class MimoTranscriptSensor(RestoreSensor, _MimoSensorBase):
    """Last transcription text — the main accuracy-diagnosis sensor."""

    _attr_icon = ICONS["last_transcript"]

    def __init__(self, stats: CallStats, device: DeviceInfo, entry_id: str | None = None) -> None:
        super().__init__(stats, device, "last_transcript", "Last transcript", entry_id=entry_id)

    @property
    def native_value(self) -> str | None:
        text = self._stats.last_transcript
        if len(text) <= 255:
            return text or None
        return text[:252] + "..."

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        text = self._stats.last_transcript
        if len(text) > 255:
            return {"full_text": text}
        return None


class MimoDurationSensor(RestoreSensor, _MimoSensorBase):
    """API round-trip duration (ms)."""

    def __init__(self, stats: CallStats, device: DeviceInfo, key: str, name: str, restore: bool, entry_id: str | None = None) -> None:
        super().__init__(stats, device, key, name, entry_id=entry_id)
        self._restore = restore

    @property
    def native_value(self) -> float | None:
        if self._key == "last_duration":
            return self._stats.last_duration_ms
        return self._stats.average_duration_ms


class MimoTokenSensor(RestoreSensor, _MimoSensorBase):
    """Token usage (chat.completions usage field when present)."""

    def __init__(self, stats: CallStats, device: DeviceInfo, key: str, name: str, enabled_default: bool = True, entry_id: str | None = None) -> None:
        super().__init__(stats, device, key, name, entry_id=entry_id)
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> int | None:
        return int(getattr(self._stats, self._key))


class MimoCostSensor(RestoreSensor, _MimoSensorBase):
    """Estimated daily cost. MiMo ASR bills ¥0.5 per hour of input audio."""

    def __init__(self, stats: CallStats, device: DeviceInfo, entry_id: str | None = None) -> None:
        super().__init__(stats, device, "cost_today", "Estimated cost today (CNY)", entry_id=entry_id)
        self._attr_icon = ICONS["cost_today"]
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> float:
        return self._stats.estimated_cost_today


class MimoAudioSensor(RestoreSensor, _MimoSensorBase):
    """Audio seconds billed today."""

    def __init__(self, stats: CallStats, device: DeviceInfo, entry_id: str | None = None) -> None:
        super().__init__(stats, device, "audio_today", "Audio seconds today", entry_id=entry_id)
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> float:
        return round(self._stats.audio_seconds_today, 1)


class MimoErrorSensor(RestoreSensor, _MimoSensorBase):
    """Last error kind ('' = ok)."""

    def __init__(self, stats: CallStats, device: DeviceInfo, entry_id: str | None = None) -> None:
        super().__init__(stats, device, "last_error", "Last error", entry_id=entry_id)
        self._attr_icon = ICONS["last_error"]

    @property
    def native_value(self) -> str | None:
        return self._stats.last_error or "ok"
