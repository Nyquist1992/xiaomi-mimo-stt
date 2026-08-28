"""Diagnostics for Xiaomi MiMo ASR — redacts api_key."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .stats import CallStats

REDACT_KEYS = {"api_key"}

if TYPE_CHECKING:
    from . import MimoASRConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MimoASRConfigEntry
) -> dict[str, Any]:
    """Return entry diagnostics (api_key redacted)."""
    stats: CallStats = entry.runtime_data.stats
    return {
        "data": async_redact_data(dict(entry.data), REDACT_KEYS),
        "stats": {
            "requests_total": stats.requests_total,
            "requests_success": stats.requests_success,
            "requests_failed": stats.requests_failed,
            "requests_today": stats.requests_today,
            "audio_seconds_today": round(stats.audio_seconds_today, 1),
            "audio_seconds_total": round(stats.audio_seconds_total, 1),
            "last_duration_ms": stats.last_duration_ms,
            "average_duration_ms": stats.average_duration_ms,
            "last_error": stats.last_error or "ok",
        },
    }
