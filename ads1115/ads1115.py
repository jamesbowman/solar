import sys
import time
import struct
import i2cdriver

from spd3303x import SPD3303X

i2=i2cdriver.I2CDriver(sys.argv[1])
i2.setspeed(400)

dev = 0x48
assert dev in i2.scan()

factor = 2.50067 / 2.4883
factor = 2.50067 / 2.4893
factor = 2.50067 / 2.4872
factor = 1

class ADS1115:
    def __init__(self, calibration = 1.0, addr = 0x48):
        self.calibration = calibration
        self.addr = addr

    # MUX selector

    A0_MINUS_A1 = 0
    A0_MINUS_A3 = 1
    A1_MINUS_A3 = 2
    A2_MINUS_A3 = 3
    A0          = 4
    A1          = 5
    A2          = 6
    A3          = 7

    def sense(self, i2, mux, pga = 0):
        cfg = (
            (1 << 15)   |
            (mux << 12) |      # 0: A0-A1, 4: A0
            (pga << 9)  |      # PGA
            (1 << 8)    | 
            (0 << 5)           # rate
        )
        i2.regwr(dev, 1, struct.pack('>H', cfg))
        while True:
            status = i2.regrd(dev, 1, '>H')
            if (status >> 15) == 1:
                break
        raw = i2.regrd(dev, 0, '>h')
        rg = [6.144, 4.096, 2.048, 1.024, 0.512, 0.256][pga]
        v = self.calibration * rg * raw / 32768
        return v

class WCS:
    def __init__(self, vdd, i0v, ipv, inv):
        # vdd nominal 5V supply
        # i0v voltage at 0 amps
        # ipv voltage at 1 amps
        # inv voltage at -1 amps
        
        A = 1
        
        # Both of these are expressed as a fraction of vdd
        self.zero = i0v / vdd
        self.per_a_p = ((ipv - i0v) / A) / vdd
        self.per_a_n = ((i0v - inv) / A) / vdd

    def v_to_a(self, v, vdd):
        nv = (v / vdd) - self.zero
        if nv <= 0:
            return nv / self.per_a_n
        else:
            return nv / self.per_a_p

class Sensor:
    def __init__(self, adc):
        self.adc = adc

    def cs(self):
        adc = self.adc
        vdd = adc.sense(i2, ADS1115.A0)
        seA = adc.sense(i2, ADS1115.A1)
        seB = adc.sense(i2, ADS1115.A2)
        frA = seA / vdd
        frB = seB / vdd
        # print(f"{vdd=} {seA=} {frA=}")
        # print(f"A {frA:.4f}  B {frB:.4f}")
        return (frA, frB)

    def calibrate(self, ch):
        ch.set_current(0.0)
        ch.set_output(True)
        for mA in range(0, 2600, 100):
            ch.set_current(mA / 1000)
            time.sleep(1)
            print(4 * mA / 1000, self.cs())
        ch.set_output(False)

if 0:
    for i in range(99999):
        pga = 0
        if 1:
            cfg = (
                (1 << 15)   |
                (4 << 12)   |      # 0: A0-A1, 4: A0
                (pga << 9)  |      # PGA
                (1 << 8)    | 
                (0 << 5)           # rate
            )
            i2.regwr(dev, 1, struct.pack('>H', cfg))
            t0 = time.time()
            while True:
                status = i2.regrd(dev, 1, '>H')
                # print(f"{cfg=:04x} {status=:04x}")
                if (status >> 15) == 1:
                    took = time.time() - t0
                    percent = abs(100 * took / 0.125)
                    # print(f"timing difference {percent:.0f}%")
                    break
        raw = i2.regrd(dev, 0, '>h')
        rg = [ 6.144, 4.096, 2.048, 1.024, 0.512, 0.256][pga]
        v = factor * rg * raw / 32768
        print(f"       {raw=:05x} {v=:.4f}")
elif 0:
    a = ADS1115(2.50067 / 2.4872)
    vdd = a.sense(i2, ADS1115.A3)
    iv = a.sense(i2, ADS1115.A0)
    print(f"{vdd=:.5f}, {iv=:.5f}")

    wcs0 = WCS(vdd=5.00490, i0v=2.62659, ipv=2.69464, inv=2.55759)
    while 1:
        iv = a.sense(i2, ADS1115.A0)
        i = wcs0.v_to_a(iv, vdd)
        vdd = a.sense(i2, ADS1115.A3)
        print(f"{i:7.3f} A")
        time.sleep(1)
else:
    adc = ADS1115(1)
    def cs():
        vdd = adc.sense(i2, ADS1115.A0)
        seA = adc.sense(i2, ADS1115.A1)
        seB = adc.sense(i2, ADS1115.A2)
        frA = seA / vdd
        frB = seB / vdd
        # print(f"{vdd=} {se=} {fr=}")
        # print(f"A {frA:.4f}  B {frB:.4f}")
        return (frA, frB)
        
    with SPD3303X.ethernet_device("192.168.1.96") as psu:
        adc = ADS1115(1)
        sensor = Sensor(adc)
        sensor.calibrate(psu.CH2)
    sys.exit(0)

    zz = cs()
    print("Zero", zz)
    ps = (0.0332 / 2, 0.0134 / 2)
    ns = (0.0330 / 2, 0.0130 / 2)
    while 1:
        (a, b) = [(x - z) for (x, z) in zip(cs(), zz)]
        # print(f"{a=:+6.4f} {b=:+6.4f}")
        def current(x, p, n):
            if x < 0:
                return x / n
            else:
                return x / p
        i = [current(x, n, p) for (x, n, p) in zip((a, b), ps, ns)]
        print(f"{a=:+6.4f} {b=:+6.4f}   {i[0]:+6.4f} {i[1]:+6.4f}")
