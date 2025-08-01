import sys
import struct
import time
import datetime
import json

def sleep_until_next_minute():
    now = datetime.datetime.now()
    next_minute = (now + datetime.timedelta(minutes=1)).replace(second=0, microsecond=0)
    sleep_duration = (next_minute - now).total_seconds()
    time.sleep(sleep_duration)

calibrations = {
    # Uncalibrated
    0x0 : dict(
        voffset = 0,
        vscale = 1,
        ioffset = 0,
        iscale = 1,
        tscale = 0,
    ),

    # Development unit
    0x99 : dict(
        voffset = 3.9,
        vscale = 10.000 / 25040,
        ioffset = 32944.4,
        iscale = 0.4977 / 420.0,
        tscale = 0,
    ),

    0x23937d6 : dict(
        voffset = 15,
        vscale = 10.000 / 25007,
        ioffset = 32777,
        iscale = 0.3680 / 317.5,
        tscale = (273.15 + 19.1) / 31649,
    ),

    0x2392dad: dict(
        voffset = 15,
        vscale = 10.000 / 25007,
        ioffset = 32858,
        iscale_p = 1 / (33678 - 32858),
        iscale_n = 1 / (32858 - 32029),
        tscale = (273.15 + 19.1) / 31649,
    ),


}

class SunGauge:

    def __init__(self, i2c, addr):
        self.i2c = i2c
        self.addr = addr

    def sample(self):
        fmt = "<QQQQI"
        rr = i2.regrd(self.addr, 0x00, struct.calcsize(fmt))
        if len(rr) != struct.calcsize(fmt):
            print("!!! Short read", len(rr), rr.hex(' '))
            return None
        (n, a, b, c, id) = struct.unpack(fmt, rr[:struct.calcsize(fmt)])
        (am, bm, cm) = [x / n for x in (a, b, c)]
        assert id in calibrations, f"Unknown id {id:#x}"
        cal = calibrations[id]

        print(f"{bm=}")
        bo = (bm - cal["ioffset"])
        if bo > 0:
            cc = bo * cal["iscale_p"]
        else:
            cc = bo * cal["iscale_n"]
        cc = round(cc, 3)

        return dict(
            n = n,
            id = id,
            raw = [n, a, b, c],
            voltage = round(max(0, (am - cal["voffset"]) * cal["vscale"]), 3),
            current = cc,
            temp =    round((cm * cal["tscale"]) - 273.15, 3),
        )

import i2cdriver
D="/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DO02C6UM-if00-port0"
D="/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DK0C3XLQ-if00-port0"
D="/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DO02C6UM-if00-port0"
i2=i2cdriver.I2CDriver(D)
print(i2)

if len(sys.argv) == 1:
    i2.scan()
    sys.exit(0)

addr = int(sys.argv[1], 0)

if addr in i2.scan():
    if 1:
        with open("soc.json", "r") as f:
            (soc, t0) = json.load(f)
        sw = SunGauge(i2, addr)
        while True:
            sleep_until_next_minute()
            s = sw.sample()
            print()
            if s is not None:
                t1 = time.time()
                if s["voltage"] > 14.09:
                    soc = 280
                else:
                    dt = (t1 - t0)
                    hf = dt / 3600
                    soc = min(280, soc + s["current"] * hf)
                t0 = t1
                s["t"] = t0
                s["soc"] = soc
                i2.getstatus()
                s["temp"] = i2.temp

                for k in ("voltage", "current", "temp", "soc"):
                    print(f"{k:10} {s[k]:.3f}")
                with open(f"/home/jamesb/tsd/sungauge40/{t0:.6f}.json", 'w') as f:
                    json.dump(s, f)
                with open("soc.json", "w") as f:
                    json.dump((soc, t0), f)

    t0 = time.time()
    for i in range(99999999999999999999):
        t = time.time()
        tr = (t - t0)
        t0 = t
        fmt = "<QQQQI"
        rr = i2.regrd(0x40, 0x00, struct.calcsize(fmt))
        # print(rr.hex(' '))
        (n, a, b, c, id) = struct.unpack(fmt, rr[:struct.calcsize(fmt)])
        if 0:
            a_v = max(0, (a / n) - 3.9)
            b_v = (b / n) - 32944.4
            c_v = c / n
        else:
            a_v = a / n
            b_v = b / n
            c_v = c / n
        # print(f"{tr:.3f}", rr.hex())
        print(f"{id:06x}: {tr:.3f}", (n, a, b, c), f"a={a_v:<6.1f} b={b_v:<6.1f} c={c_v:<6.1f}")
        v = 10.000 * a_v / 25040
        i = 0.4977 * b_v / 420.0
        # print(f"v={v:.3f} i={i:.3f}")
        time.sleep(60)
