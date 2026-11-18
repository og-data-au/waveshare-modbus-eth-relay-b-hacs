
"""The Waveshare Relay B integration."""
from __future__ import annotations

import voluptuous as vol

from pymodbus.client import AsyncModbusTcpClient

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import WaveshareConfigEntry, WaveshareCoordinator

SERVICE_PULSE_RELAY = "pulse_relay"

PULSE_SCHEMA = vol.Schema(
    {
        vol.Required("relay"): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=8),
        ),
        vol.Optional("duration_ms", default=500): vol.All(
            vol.Coerce(int),
            vol.Range(min=100, max=60000),
            lambda value: (
                value
                if value % 100 == 0
                else vol.Invalid("Must be a multiple of 100 ms")
            ),
        ),
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaveshareConfigEntry,
) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        DEFAULT_SCAN_INTERVAL,
    )

    client = AsyncModbusTcpClient(host, port=port)
    coordinator = WaveshareCoordinator(
        hass,
        client,
        scan_interval,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    async def handle_pulse(call: ServiceCall) -> None:
        relay = call.data["relay"]
        duration_ms = call.data["duration_ms"]

        await coordinator.async_pulse_relay(
            relay - 1,
            duration_ms,
        )

    if not hass.services.has_service(
        DOMAIN,
        SERVICE_PULSE_RELAY,
    ):
        hass.services.async_register(
            DOMAIN,
            SERVICE_PULSE_RELAY,
            handle_pulse,
            schema=PULSE_SCHEMA,
        )

    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: WaveshareConfigEntry,
) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unloaded:
        entry.runtime_data.client.close()

        if not hass.config_entries.async_entries(DOMAIN) or all(
            other.entry_id == entry.entry_id
            for other in hass.config_entries.async_entries(DOMAIN)
        ):
            hass.services.async_remove(
                DOMAIN,
                SERVICE_PULSE_RELAY,
            )

    return unloaded


async def _async_update_listener(
    hass: HomeAssistant,
    entry: WaveshareConfigEntry,
) -> None:
    await hass.config_entries.async_reload(
        entry.entry_id
    )
