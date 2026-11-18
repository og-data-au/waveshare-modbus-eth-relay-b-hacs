
# Waveshare Modbus POE ETH Relay (B) — Home Assistant Integration

**OG DATA Edition — Hardware-Timed Relay Control**

A [HACS](https://hacs.xyz/) custom integration for the **Waveshare Modbus POE ETH Relay (B)** board.

This integration provides **8 digital inputs**, **8 relay outputs**, and **native hardware-timed relay pulses** over Modbus TCP.

Originally developed by [sacherjj](https://github.com/sacherjj/waveshare-modbus-eth-relay-b-HACS), with additional functionality developed by **OG DATA**.

## Why This Integration?

Home Assistant's built-in Modbus integration can poll individual entities with separate network requests. With 8 inputs and 8 relays, this can mean up to 16 round-trips per polling cycle.

This integration reads all 8 inputs in **one** Modbus request and all 8 relays in **one** Modbus request — just **two requests per polling cycle**.

No MQTT broker, no external daemon, and no cloud services.

It uses `local_polling` via [pymodbus](https://github.com/pymodbus-dev/pymodbus) and communicates directly with the board over your local network.

For responsive digital inputs, polling at approximately **1 second** may be desirable.

### What's New in the OG DATA Edition?

- **Native hardware-timed relay pulses** using Waveshare's special Modbus commands.
- Configurable pulse durations in 100 ms increments.
- Dedicated `waveshare_relay_b.pulse_relay` Home Assistant action.
- Serialized Modbus operations using `asyncio.Lock`.
- Improved connection handling and error reporting.
- All original relay switching and digital input functionality retained.

## Hardware Configuration

The board must first be configured using the manufacturer's interface.

See the [Waveshare documentation](https://www.waveshare.com/wiki/Modbus_POE_ETH_Relay_(B)).

Recommended settings:

| Setting | Value |
|---|---|
| Work Mode | TCP Server |
| Protocol | Modbus TCP to RTU |
| TCP Port | 502 |
| Modbus Unit ID | 1 |
| IP Address | Static IP or DHCP reservation |

## Installation via HACS

1. Open **HACS** in Home Assistant.
2. Click the three-dot menu (⋮) and select **Custom repositories**.
3. Add the URL of your OG DATA GitHub fork.
4. Select **Integration** as the category.
5. Click **Add**.
6. Find **Waveshare Modbus Relay B** and click **Download**.
7. Restart Home Assistant.

**Note:** If you previously installed the original integration, back up your configuration before switching repositories. Do not install two versions using the same integration domain.

## Adding the Integration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Waveshare Modbus Relay B**.
3. Enter the configuration details:
   - **Host** — IP address or hostname of the board.
   - **Port** — Modbus TCP port (default: `502`).
   - **Scan Interval** — Polling frequency in seconds (default: `5`).
4. Click **Submit**.

Home Assistant will create a device containing all 16 entities.

The scan interval can be changed later via **Settings → Devices & Services → Configure**.

## Entity Model

Each configured board appears as a single Home Assistant device with 16 entities:

| Platform | Entities | Description |
|---|---|---|
| `binary_sensor` | Input 1 – Input 8 | Physical digital inputs |
| `switch` | Relay 1 – Relay 8 | Independently controllable relay outputs |

Relay states are confirmed through Modbus read-back.

The Modbus unit ID is fixed at **1**.

## Hardware-Timed Relay Pulses

The OG DATA edition introduces **native hardware-timed relay control**.

Instead of switching a relay on, waiting in Home Assistant, and then switching it off, a single Modbus command instructs the Waveshare controller to perform the entire pulse.

The relay automatically releases after the specified duration, independently of Home Assistant.

### How It Works

The Waveshare uses a special implementation of **Modbus function 05 — Write Single Coil**.

| Parameter | Value |
|---|---|
| Function Code | `0x05` |
| Relay 1 Pulse Address | `0x0200` |
| Relay 2 Pulse Address | `0x0201` |
| Relay 8 Pulse Address | `0x0207` |
| Duration Resolution | 100 ms |
| Default Pulse Duration | 500 ms |

For example, a 500 ms pulse uses a duration value of `5`.

The controller activates the selected relay and automatically releases it after 500 ms.

### Home Assistant Action

The integration registers:

`waveshare_relay_b.pulse_relay`

**Example — Pulse Relay 1 for 500 ms:**

```yaml
action: waveshare_relay_b.pulse_relay
data:
  relay: 1
  duration_ms: 500
```

**Example — Pulse Relay 4 for 1 second:**

```yaml
action: waveshare_relay_b.pulse_relay
data:
  relay: 4
  duration_ms: 1000
```

### Action Parameters

| Parameter | Required | Description |
|---|---|---|
| `relay` | Yes | Relay channel number (1–8) |
| `duration_ms` | No | Pulse duration in milliseconds (default: 500) |

The integration accepts durations from **100 to 60,000 ms**, in increments of 100 ms. Actual supported durations depend on the controller firmware.

### Advantages of Hardware-Timed Pulses

- No Home Assistant delay scripts required.
- No separate relay-off command required.
- Precise timing controlled by the Waveshare hardware.
- Relay automatically releases even if Home Assistant disconnects after the command is accepted.
- Useful for momentary pushbutton interfaces and compatible equipment controllers.

**Safety:** Hardware-timed pulses do not replace the safety systems of connected equipment. Verify electrical compatibility and implement appropriate command interlocking.

## Digital Inputs

All eight physical digital inputs are exposed as Home Assistant binary sensors.

Typical applications include:

- Magnetic reed switches.
- Door open/closed detection.
- Dry-contact pushbuttons.
- Equipment status monitoring.
- Limit switches.

All eight inputs are read in a single Modbus request per polling cycle.

Input responsiveness depends on the configured polling interval.

## Connection Management

The integration uses a shared asynchronous Modbus TCP client.

An `asyncio.Lock` serializes polling and relay control commands, preventing overlapping operations on the same connection.

Automatic reconnection is attempted when the connection becomes unavailable.

## Current Limitations

The following features are not yet implemented or fully supported:

- **Hardware relay toggle commands** — native timed pulses are supported, but additional board-specific commands are not exposed.
- **Per-channel control modes and linkage** — board-specific register configuration.
- **Multiple-board pulse targeting** — the current pulse action is intended for a single configured board.
- **Relay command interlocking** — mutually exclusive relay commands must be coordinated separately.
- **TLS/authentication** — the board does not support encrypted Modbus TCP.

Multiple boards can be configured as separate integration entries for ordinary input monitoring and relay switching. Pulse action routing across multiple boards requires further development.

## Requirements

- Home Assistant with a compatible Python and pymodbus environment.
- Waveshare Modbus POE ETH Relay (B).
- Network access to the board over TCP port 502 (or configured alternative).
- `pymodbus` 3.13.1 or compatible version, installed automatically through Home Assistant.

## Development and Testing

Hardware-timed pulse functionality has been tested on a physical Waveshare Modbus POE ETH Relay (B) running with Home Assistant OS.

A **500 ms hardware pulse** was successfully executed, with the relay activating and automatically releasing.

Digital input testing of the modified integration is ongoing.

## Credits

**Original Integration:** [sacherjj](https://github.com/sacherjj/waveshare-modbus-eth-relay-b-HACS)

**Additional Development and Maintenance:** OG DATA

This project is based on the original integration and retains attribution to its author.

## License

MIT — see [LICENSE](LICENSE).

This project is an independent community integration and is not officially affiliated with Waveshare or Home Assistant.
