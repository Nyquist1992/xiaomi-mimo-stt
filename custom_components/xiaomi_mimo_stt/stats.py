"""In-memory call statistics for Xiaomi MiMo ASR.

Shared between the STT entity (writer) and diagnostic sensors (readers).
Pure Python — no HA framework imports.

MiMo ASR billing is AUDIO DURATION based (¥0.5/h / $0.074/h), NOT tokens.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date


AVG_WINDOW = 20
# Official pricing per audio hour (https://mimo.mi.com/docs/price):
CNY_PER_AUDIO_HOUR = 0.5
USD_PER_AUDIO_HOUR = 0.074


@dataclass
class CallStats:
    """Mutable stats store."""

    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    requests_today: int = 0
    # Billing for MiMo ASR is per hour of input audio (NOT tokens).
    audio_seconds_today: float = 0.0
    audio_seconds_total: float = 0.0
    last_duration_ms: float | None = None
    last_transcript: str = ""
    last_error: str = ""  # "", "auth", "timeout", "api", "connection", "empty"
    duration_history: deque[float] = field(default_factory=lambda: deque(maxlen=AVG_WINDOW))
    _stats_date: date = field(default_factory=date.today)

    _listeners: list[Callable[[], None]] = field(default_factory=list, repr=False)

    def add_listener(self, fn: Callable[[], None]) -> None:
        self._listeners.append(fn)

    def _notify(self) -> None:
        for fn in self._listeners:
            try:
                fn()
            except Exception:  # noqa: BLE001 — sensor callback must not break STT
                pass

    def _roll_day(self) -> None:
        today = date.today()
        if today != self._stats_date:
            self._stats_date = today
            self.requests_today = 0
            self.audio_seconds_today = 0.0

    def record_start(self) -> None:
        self._roll_day()
        self.requests_total += 1
        self.requests_today += 1

    def record_success(
        self,
        transcript: str,
        duration_ms: float,
        audio_seconds: float,
    ) -> None:
        self._roll_day()
        self.requests_success += 1
        self.last_transcript = transcript
        self.last_duration_ms = round(duration_ms, 1)
        self.last_error = ""
        self.duration_history.append(duration_ms)
        self.audio_seconds_today += audio_seconds
        self.audio_seconds_total += audio_seconds
        self._notify()

    def record_failure(self, error_kind: str, duration_ms: float) -> None:
        self._roll_day()
        self.requests_failed += 1
        self.last_error = error_kind
        self.last_duration_ms = round(duration_ms, 1)
        self._notify()

    @property
    def average_duration_ms(self) -> float | None:
        if not self.duration_history:
            return None
        return round(sum(self.duration_history) / len(self.duration_history), 1)

    @property
    def estimated_cost_today_usd(self) -> float:
        """$0.074 per audio hour → /3600 per second, rounded to 4 decimals."""
        return round(self.audio_seconds_today * USD_PER_AUDIO_HOUR / 3600.0, 4)

    @property
    def estimated_cost_today_cny(self) -> float:
        """¥0.5 per audio hour → /3600 per second, rounded to 4 decimals."""
        return round(self.audio_seconds_today * CNY_PER_AUDIO_HOUR / 3600.0, 4)
