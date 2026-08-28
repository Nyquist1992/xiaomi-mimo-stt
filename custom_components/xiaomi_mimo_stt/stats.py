"""In-memory call statistics for Xiaomi MiMo ASR.

Shared between the STT entity (writer) and diagnostic sensors (readers).
Pure Python — no HA framework imports.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date


AVG_WINDOW = 20


@dataclass
class CallStats:
    """Mutable stats store."""

    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    requests_today: int = 0
    tokens_last: int = 0
    tokens_today: int = 0
    total_tokens: int = 0
    # Billing for MiMo ASR is ¥0.5 per hour of input audio (NOT tokens).
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
            self.tokens_today = 0
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
        tokens: int = 0,
    ) -> None:
        self._roll_day()
        self.requests_success += 1
        self.last_transcript = transcript
        self.last_duration_ms = round(duration_ms, 1)
        self.last_error = ""
        self.duration_history.append(duration_ms)
        self.tokens_last = tokens
        self.tokens_today += tokens
        self.total_tokens += tokens
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
    def tokens_total(self) -> int:
        """Alias for sensor key 'tokens_total'."""
        return self.total_tokens

    @property
    def estimated_cost_today(self) -> float:
        """¥0.5 per audio hour → ¥0.5/3600 per second, rounded to 4 decimals."""
        return round(self.audio_seconds_today * 0.5 / 3600.0, 4)
