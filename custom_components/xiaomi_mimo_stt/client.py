"""Xiaomi MiMo ASR API client.

Pure Python — accepts an injected aiohttp.ClientSession. Must NOT import the
HA framework (same boundary contract as the xiaomi-mimo-tts reference project).
"""

from __future__ import annotations

import base64
import io
import json
import logging
import time
import wave
from typing import Any, Final

import aiohttp

__all__ = ["DEFAULT_BASE_URL", "MimoASRClient", "MimoASRError"]

_LOGGER = logging.getLogger(__name__)

DEFAULT_BASE_URL: Final = "https://api.xiaomimimo.com/v1"


class MimoASRError(Exception):
    """Base error."""


class MimoASRAuthError(MimoASRError):
    """401 / 403 — invalid or revoked API key."""


class MimoASRConnectionError(MimoASRError):
    """Network-level failure."""


class MimoASRApiError(MimoASRError):
    """Non-2xx response from the MiMo API."""


def pcm_to_wav_base64(
    pcm: bytes,
    sample_rate: int,
    channels: int,
    bits_per_sample: int = 16,
) -> str:
    """Wrap raw PCM bytes into a WAV container and return the base64 string.

    MiMo ASR accepts data:audio/wav;base64 payloads only.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(bits_per_sample // 8)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return base64.b64encode(buf.getvalue()).decode("ascii")


class MimoASRClient:
    """Async HTTP client for the Xiaomi MiMo ASR API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        # Same header scheme as the MiMo TTS client ("api-key", not Bearer).
        return {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }

    async def validate(self) -> bool:
        """Probe GET /v1/models. Free, validates auth. Raises on failure."""
        url = f"{self._base_url}/models"
        try:
            async with self._session.get(
                url,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=8.0),
            ) as resp:
                if resp.status in (401, 403):
                    raise MimoASRAuthError(f"HTTP {resp.status}: invalid API key")
                if resp.status >= 400:
                    body = await self._safe_json(resp)
                    msg = (body or {}).get("error", {}).get(
                        "message", f"HTTP {resp.status}"
                    )
                    raise MimoASRApiError(msg)
                await resp.json()
        except TimeoutError as exc:
            raise MimoASRConnectionError("validate timed out") from exc
        except aiohttp.ClientConnectionError as exc:
            raise MimoASRConnectionError(str(exc)) from exc
        return True

    async def transcribe_pcm(
        self,
        pcm: bytes,
        sample_rate: int,
        channels: int,
        bits_per_sample: int = 16,
        language: str = "zh",
    ) -> tuple[str, int]:
        """Transcribe raw PCM audio. Returns (text, usage_total_tokens)."""
        audio_b64 = pcm_to_wav_base64(pcm, sample_rate, channels, bits_per_sample)
        _LOGGER.debug("MiMo ASR payload size (b64): %d bytes", len(audio_b64))
        return await self.transcribe_b64(audio_b64, mime="audio/wav", language=language)

    async def transcribe_b64(
        self,
        audio_b64: str,
        mime: str = "audio/wav",
        language: str = "zh",
    ) -> tuple[str, int]:
        """Transcribe a base64 wav/mp3 payload. Returns (text, usage_total_tokens)."""
        url = f"{self._base_url}/chat/completions"
        body: dict[str, Any] = {
            "model": "mimo-v2.5-asr",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:{mime};base64,{audio_b64}"
                            },
                        }
                    ],
                }
            ],
            # Official curl example sends asr_options as a TOP-LEVEL body
            # field (extra_body in the SDK example is an OpenAI-SDK-side
            # flatten). Keep it top-level for raw HTTP calls.
            "asr_options": {"language": language},
        }
        start = time.monotonic()
        try:
            async with self._session.post(
                url,
                headers=self._headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as resp:
                if resp.status in (401, 403):
                    raise MimoASRAuthError(f"HTTP {resp.status}: invalid API key")
                if resp.status >= 400:
                    err_body = await self._safe_json(resp)
                    msg = (
                        (err_body or {}).get("error", {}).get("message")
                        or f"HTTP {resp.status}"
                    )
                    raise MimoASRApiError(msg)
                payload = await resp.json()
        except TimeoutError as exc:
            raise MimoASRConnectionError("transcribe timed out") from exc
        except aiohttp.ClientConnectionError as exc:
            raise MimoASRConnectionError(str(exc)) from exc

        self.last_duration_ms = (time.monotonic() - start) * 1000.0

        try:
            text: str = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            _LOGGER.warning("Unexpected MiMo ASR response shape: %s", payload)
            raise MimoASRApiError("unexpected response shape") from exc

        usage = payload.get("usage") or {}
        tokens = int(usage.get("total_tokens") or 0)
        return (text or "").strip(), tokens

    async def _safe_json(self, resp: aiohttp.ClientResponse) -> dict[str, Any] | None:
        try:
            return await resp.json()
        except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError):
            return None
