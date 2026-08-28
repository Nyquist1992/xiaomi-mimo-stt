"""Config flow for Xiaomi MiMo ASR (STT).

UI first-run: enter API key (validated live against GET /v1/models).
Reconfigure / reauth flows let you swap the key later without YAML.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .client import (
    DEFAULT_BASE_URL,
    MimoASRApiError,
    MimoASRAuthError,
    MimoASRClient,
    MimoASRConnectionError,
)
from .const import (
    CONF_BASE_URL,
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DEFAULT_NAME,
    DOMAIN,
    LANGUAGE_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_API_KEY): str,
    }
)

REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})

RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): SelectSelector(
            SelectSelectorConfig(
                options=LANGUAGE_OPTIONS,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


async def _validate_api_key(
    hass: HomeAssistant, api_key: str, base_url: str = DEFAULT_BASE_URL
) -> str | None:
    """Validate api_key against MiMo. Returns errors["base"] key or None."""
    session = async_get_clientsession(hass)
    client = MimoASRClient(session, api_key=api_key, base_url=base_url)
    try:
        await client.validate()
    except MimoASRAuthError:
        return "invalid_api_key"
    except MimoASRConnectionError:
        return "cannot_connect"
    except MimoASRError:
        return "unknown"
    return None


class XiaomiMimoSTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle the config flow for Xiaomi MiMo ASR."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

        api_key = user_input[CONF_API_KEY].strip()
        unique_id = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        error = await _validate_api_key(self.hass, api_key)
        if error is not None:
            return self.async_show_form(
                step_id="user", data_schema=USER_SCHEMA, errors={"base": error}
            )

        title = (user_input.get(CONF_NAME) or "").strip() or DEFAULT_NAME
        return self.async_create_entry(
            title=title,
            data={
                CONF_API_KEY: api_key,
                CONF_BASE_URL: DEFAULT_BASE_URL,
                CONF_LANGUAGE: DEFAULT_LANGUAGE,
            },
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm", data_schema=REAUTH_SCHEMA
            )
        api_key = user_input[CONF_API_KEY].strip()
        error = await _validate_api_key(self.hass, api_key)
        if error is not None:
            return self.async_show_form(
                step_id="reauth_confirm", data_schema=REAUTH_SCHEMA, errors={"base": error}
            )
        return self.async_update_and_abort(
            self._reauth_entry, data={**self._reauth_entry.data, CONF_API_KEY: api_key}
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self._get_reconfigure_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_LANGUAGE,
                            description={
                                "suggested_value": entry.data.get(
                                    CONF_LANGUAGE, DEFAULT_LANGUAGE
                                )
                            },
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=LANGUAGE_OPTIONS,
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(CONF_API_KEY): str,
                    }
                ),
            )
        api_key = user_input[CONF_API_KEY].strip()
        error = await _validate_api_key(self.hass, api_key)
        if error is not None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_LANGUAGE): SelectSelector(
                            SelectSelectorConfig(
                                options=LANGUAGE_OPTIONS,
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(CONF_API_KEY): str,
                    }
                ),
                errors={"base": error},
            )
        return self.async_update_and_abort(
            entry,
            data={
                **entry.data,
                CONF_API_KEY: api_key,
                CONF_LANGUAGE: user_input.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            },
        )
