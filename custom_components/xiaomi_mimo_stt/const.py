"""Constants for the Xiaomi MiMo ASR (STT) integration."""

from __future__ import annotations

DOMAIN = "xiaomi_mimo_stt"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_LANGUAGE = "language"
CONF_NAME = "name"

DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_LANGUAGE = "zh"
DEFAULT_NAME = "Xiaomi MiMo ASR"
REQUEST_TIMEOUT_S = 30.0
VALIDATE_TIMEOUT_S = 8.0
MODEL_ASR = "mimo-v2.5-asr"

# MiMo ASR accepts wav/mp3, base64-encoded, up to 10 MB of base64 string.
MAX_AUDIO_BYTES = 7 * 1024 * 1024  # raw PCM cap before wav+b64 (safety margin)

# Languages supported by MiMo ASR asr_options.language
LANGUAGE_OPTIONS = ["auto", "zh", "en"]

# Languages this STT entity advertises to Home Assistant.
# Include zh-tw / zh-hk / zh-hant so HA loads Traditional-Chinese intents
# (we map them down to "zh" for the API, mirroring the Whisper community
# integration approach).
SUPPORTED_LANGUAGES = [
    "zh",
    "zh-cn",
    "zh-tw",
    "zh-hk",
    "zh-hans",
    "zh-hant",
    "en",
    "auto",
]

LANGUAGE_TO_MIMO: dict[str, str] = {
    "zh": "zh",
    "zh-cn": "zh",
    "zh-tw": "zh",
    "zh-hk": "zh",
    "zh-hans": "zh",
    "zh-hant": "zh",
    "en": "en",
}
