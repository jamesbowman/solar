# LiTime MPPT reader on cam1

Controller: `BT-LTMPPT2430`, Bluetooth address `C8:47:80:63:1B:C3`.
The reader sends only Modbus function 03 (read holding registers), requesting
19 registers starting at `0x0101` over BLE characteristic `ffe1`.
It prints one JSON object per sample to stdout, with Unix timestamp `t`, units
in the metric names, all 19 raw registers, and the full response in hex.
Diagnostics go to stderr. Default polling interval is 10 seconds.

## Run on cam1

The service runs the checkout in `/home/jamesb/solar`. Python dependencies
remain in the existing isolated environment `/home/jamesb/litime-monitor/.venv`.

```sh
# Stop the background reader before running another Bluetooth client.
sudo systemctl stop litime-monitor
cd /home/jamesb/solar
/home/jamesb/litime-monitor/.venv/bin/python litime_mppt.py --samples 3 --debug
/home/jamesb/litime-monitor/.venv/bin/python litime_mppt.py --mqtt-host pi --mqtt-topic litime
```

Omit `--samples` to run continuously. Omit `--mqtt-host` for stdout only.
The phone must disconnect before cam1 can connect; stop the service to use
the phone app again. No unpairing or password is needed to read telemetry.

## Service and MQTT

`litime-monitor.service` runs as `jamesb`, starts on boot, and sends the same
JSON to `pi:1883`, topic `litime`. It reconnects after Bluetooth failures and
independently reconnects to MQTT. Broker outages leave stdout logging working.
MQTT is live, QoS 0, non-retained, without offline replay. Missing updates
must be treated as stale by consumers using `t`. No MQTT control topics exist.

```sh
sudo systemctl restart litime-monitor
systemctl status litime-monitor
journalctl -u litime-monitor -f -o cat
```

After pulling code updates into `/home/jamesb/solar`, restart the service.
If the unit file changes, install it and reload systemd before restarting:

```sh
sudo install -m 644 /home/jamesb/solar/litime-monitor.service /etc/systemd/system/litime-monitor.service
sudo systemctl daemon-reload
sudo systemctl restart litime-monitor
```

To install elsewhere, create a venv, install `litime-requirements.txt`, copy
the Python file, and adapt the paths/user/broker in the service file before
installing it under `/etc/systemd/system/` and enabling it with systemctl.
The broker defaults follow this repository's existing `mqttlog.py` configuration.

## Decoding scope

Decoded fields: battery voltage/current/power, controller temperature, load
voltage/current/status, panel voltage, peak charge power today, energy today,
running days, and 32-bit total energy. These use the community register map;
the live controller responds with valid CRCs and plausible readings.
An independent comparison against the phone display is still useful.

All returned registers are preserved, including unknown ones. This covers
the known live telemetry block, not an exhaustive map of every register,
configuration setting, or historical record in the device. No separate panel
current is identified in this block. `load_power_raw` deliberately has no
physical unit: the references disagree between W and 0.1 W. Temperature is
the high byte of `0x0105`; negative-temperature encoding is unverified.
The meaning of `0x0101` (observed 100), `0x010c`, `0x010e`, `0x0112`, and
`0x0113`, and the low temperature byte (observed `0xff`) is not assumed.
Unknown load status codes remain `unknown` with their raw value intact.

Protocol facts were cross-checked against these independently published readers:

- https://github.com/tomhollingworth/litime-monitor/blob/4dafddcf60f0488ff64beee68ae226502cd81b04/domain/types.go
- https://github.com/mavenius/litime_mppt_esphome/blob/main/litime_solar_mppt.h
- https://github.com/mavenius/litime_mppt_esphome/blob/main/litime_solar_mppt.yaml

The Python transport and parser are a new implementation. Responses are
reassembled across BLE notification boundaries and validated by length,
header, and Modbus CRC before any sample is emitted. A timeout forces a fresh
connection, avoiding association of a late reply with the next poll.

## Tests

```sh
python3 -m unittest -v test_litime_mppt
```

Tests use a captured controller response, all fragment boundaries, corrupt
frames, noise, Modbus exceptions, unknown statuses, and 32-bit energy values.

Live validation on 2026-09-12: all eight tests passed locally and on cam1;
an independent subscriber received three samples from `pi:1883` on `litime`.
The service resumed valid telemetry after a deliberate Bluetooth disconnect
without a process restart. Occasional incomplete/missing responses were also
observed: these cause a timeout and reconnect, so sampling gaps are possible.
