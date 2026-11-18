
"""DataUpdateCoordinator for the Waveshare Relay B integration."""
from __future__ import annotations

import asyncio
import logging
import struct
from datetime import timedelta

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu.bit_message import WriteSingleCoilRequest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import CHANNELS, DOMAIN, UNIT_ID
from .helpers import any_error, coalesce_bits

_LOGGER = logging.getLogger(__name__)

type WaveshareConfigEntry = ConfigEntry["WaveshareCoordinator"]


class WaveshareCoordinator(
    DataUpdateCoordinator[dict[str, list[bool]]]
):
    """Poll inputs and relays; control relays over Modbus TCP."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: AsyncModbusTcpClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._lock = asyncio.Lock()

    async def _ensure_connected(self) -> None:
        """Connect or reconnect the shared Modbus client."""
        if not self.client.connected:
            if not await self.client.connect():
                raise UpdateFailed(
                    "Cannot connect to Waveshare relay"
                )

    async def _async_update_data(
        self,
    ) -> dict[str, list[bool]]:
        """Read all eight inputs and relay states."""
        try:
            async with self._lock:
                await self._ensure_connected()

                di = await self.client.read_discrete_inputs(
                    0,
                    count=CHANNELS,
                    device_id=UNIT_ID,
                )
                co = await self.client.read_coils(
                    0,
                    count=CHANNELS,
                    device_id=UNIT_ID,
                )

        except (
            ModbusException,
            ConnectionError,
            OSError,
        ) as err:
            raise UpdateFailed(
                f"Modbus read failed: {err}"
            ) from err

        if any_error(di, co):
            raise UpdateFailed(
                "Modbus response reported an error"
            )

        return {
            "inputs": coalesce_bits(di.bits, CHANNELS),
            "relays": coalesce_bits(co.bits, CHANNELS),
        }

    async def async_set_relay(
        self,
        index: int,
        value: bool,
    ) -> None:
        """Switch a relay on or off normally."""
        if not 0 <= index < CHANNELS:
            raise ValueError("Invalid relay index")

        try:
            async with self._lock:
                await self._ensure_connected()

                result = await self.client.write_coil(
                    index,
                    value,
                    device_id=UNIT_ID,
                )

        except (
            ModbusException,
            ConnectionError,
            OSError,
        ) as err:
            raise UpdateFailed(
                f"Modbus write failed: {err}"
            ) from err

        if result.isError():
            raise UpdateFailed(
                "Modbus write reported an error"
            )

        await self.async_request_refresh()

    async def async_pulse_relay(
        self,
        index: int,
        duration_ms: int = 500,
    ) -> None:
        """Trigger a native hardware-timed relay pulse.

        Waveshare uses Modbus FC05 at 0x0200 + index.
        The value field contains duration in 100 ms ticks,
        rather than the standard boolean coil value.
        """
        if not 0 <= index < CHANNELS:
            raise ValueError(
                "Relay index must be between 0 and 7"
            )

        if (
            not 100 <= duration_ms <= 60000
            or duration_ms % 100 != 0
        ):
            raise ValueError(
                "Duration must be 100–60000 ms "
                "in 100 ms increments"
            )

        address = 0x0200 + index
        ticks = duration_ms // 100

        # Build a normal FC05 request, then replace
        # its encoded payload with Waveshare's special
        # address + pulse-duration format.
        request = WriteSingleCoilRequest(
            address=address,
            bits=[True],
            dev_id=UNIT_ID,
        )

        request.encode = lambda: struct.pack(
            ">HH",
            address,
            ticks,
        )

        try:
            async with self._lock:
                await self._ensure_connected()

                result = await self.client.execute(
                    False,
                    request,
                )

        except (
            ModbusException,
            ConnectionError,
            OSError,
        ) as err:
            raise UpdateFailed(
                f"Hardware pulse failed: {err}"
            ) from err

        if result.isError():
            raise UpdateFailed(
                "Hardware pulse command rejected"
            )

        _LOGGER.debug(
            "Hardware pulse: relay %d, duration %d ms",
            index + 1,
            duration_ms,
        )

        # The Waveshare turns the relay off itself.
        # No Home Assistant delay is needed.
        await self.async_request_refresh()
