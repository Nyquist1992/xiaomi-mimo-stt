"""Xiaomi MiMo ASR speech-to-text entity.

Input contract (HA Assist):
  - PCM s16le audio streamed in chunks over AsyncIterable[bytes]
  - metadata carries sample_rate / channel / bit_rate / codec / format
  - we buffer, wrap into WAV, base64-encode, POST to MiMo ASR
Output contract:
  - SpeechResult(text, SUCCESS/ERROR) — text goes back into the pipeline

MiMo ASR API (https://mimo.mi.com):
  POST {base_url}/chat/completions
  model: mimo-v2.5-asr
  content: [{type: "input_audio", input_audio: {data: "data:audio/wav;base64,..."}}]
  asr_options: {language: auto|zh|en}   ← top-level body field
  → text at choices[0].message.content, token usage at usage.total_tokens
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterable

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import MimoASRApiError, MimoASRAuthError, MimoASRClient, MimoASRConnectionError
from .const import (
    CONF_BASE_URL,
    CONF_LANGUAGE,
    DOMAIN,
    LANGUAGE_TO_MIMO,
    MAX_AUDIO_BYTES,
    SUPPORTED_LANGUAGES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MiMo ASR STT entity from a config entry."""
    session = async_get_clientsession(hass)
    client = MimoASRClient(
        session,
        api_key=config_entry.data[CONF_API_KEY],
        base_url=config_entry.data.get(CONF_BASE_URL, "https://api.xiaomimimo.com/v1"),
    )
    async_add_entities(
        [
            MimoSTREntity(
                client=client,
                stats=config_entry.runtime_data.stats,
                name=config_entry.data.get(CONF_NAME, "Xiaomi MiMo ASR"),
                default_language=config_entry.data.get(CONF_LANGUAGE, "zh"),
                unique_id=config_entry.entry_id,
            )
        ]
    )


class MimoSTREntity(SpeechToTextEntity):
    """Xiaomi MiMo ASR provider entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "mimo_stt"

    def __init__(
        self,
        client: MimoASRClient,
        stats,
        name: str,
        default_language: str,
        unique_id: str,
    ) -> None:
        """Init the STT entity."""
        self._client = client
        self._stats = stats
        self._default_language = default_language
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=name,
            manufacturer="Xiaomi",
            model="MiMo-V2.5-ASR",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str]:
        """Return languages this entity accepts from pipelines."""
        return SUPPORTED_LANGUAGES

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """HA Assist streams WAV/PCM containers to STT."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Only PCM codec (raw s16le)."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """16-bit PCM (s16le) — what HA Assist streams."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Typical Assist rates; MiMo accepts the wav container of any of these."""
        return [
            AudioSampleRates.SAMPLERATE_8000,
            AudioSampleRates.SAMPLERATE_16000,
            AudioSampleRates.SAMPLERATE_44100,
            AudioSampleRates.SAMPLERATE_48000,
        ]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Mono is what every Assist satellite streams; stereo accepted too."""
        return [AudioChannels.CHANNEL_MONO, AudioChannels.CHANNEL_STEREO]

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Buffer PCM, wrap in WAV, base64, and POST to MiMo ASR."""
        pcm = bytearray()
        async for chunk in stream:
            pcm.extend(chunk)
            if len(pcm) > MAX_AUDIO_BYTES:
                _LOGGER.error(
                    "Audio stream exceeds %d bytes limit for MiMo ASR",
                    MAX_AUDIO_BYTES,
                )
                self._stats.record_failure("empty", 0.0)
                return SpeechResult("", SpeechResultState.ERROR)

        if not pcm:
            _LOGGER.error("No audio data received from pipeline")
            self._stats.record_failure("empty", 0.0)
            return SpeechResult("", SpeechResultState.ERROR)

        audio_seconds = len(pcm) / (metadata.sample_rate * 2)  # s16le = 2 bytes

        # Map HA pipeline language (zh-tw etc.) to MiMo's language option.
        lang = (metadata.language or self._default_language or "zh").lower()
        mimo_lang = LANGUAGE_TO_MIMO.get(lang, "auto")

        _LOGGER.debug(
            "MiMo ASR: %d bytes PCM (%.1fs), rate=%d ch=%d lang=%s",
            len(pcm),
            audio_seconds,
            metadata.sample_rate,
            metadata.channel,
            mimo_lang,
        )

        self._stats.record_start()
        start = time.monotonic()
        try:
            text, tokens = await self._client.transcribe_pcm(
                pcm=bytes(pcm),
                sample_rate=metadata.sample_rate,
                channels=metadata.channel,
                bits_per_sample=16,
                language=mimo_lang,
            )
        except MimoASRAuthError as exc:
            _LOGGER.error("MiMo ASR auth failed: %s", exc)
            self._stats.record_failure("auth", (time.monotonic() - start) * 1000)
            return SpeechResult("", SpeechResultState.ERROR)
        except MimoASRConnectionError as exc:
            _LOGGER.error("MiMo ASR connection failed: %s", exc)
            self._stats.record_failure("connection", (time.monotonic() - start) * 1000)
            return SpeechResult("", SpeechResultState.ERROR)
        except MimoASRApiError as exc:
            _LOGGER.error("MiMo ASR request failed: %s", exc)
            self._stats.record_failure("api", (time.monotonic() - start) * 1000)
            return SpeechResult("", SpeechResultState.ERROR)
        except Exception:  # noqa: BLE001 — never crash the pipeline
            _LOGGER.exception("Unexpected error during MiMo ASR transcription")
            self._stats.record_failure("api", (time.monotonic() - start) * 1000)
            return SpeechResult("", SpeechResultState.ERROR)

        duration_ms = (time.monotonic() - start) * 1000

        if not text:
            _LOGGER.warning("MiMo ASR returned empty transcript")
            self._stats.record_failure("empty", duration_ms)
            return SpeechResult("", SpeechResultState.FAIL)

        self._stats.record_success(
            transcript=text,
            duration_ms=duration_ms,
            audio_seconds=audio_seconds,
            tokens=tokens,
        )
        _LOGGER.debug("MiMo ASR transcript (%d ms): %s", duration_ms, text)
        return SpeechResult(text, SpeechResultState.SUCCESS)
