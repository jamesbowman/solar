import os
import sys
import time
import json

dir= "/home/jamesb/tsd/sungauge40"
samples = [dir + "/" + fn for fn in os.listdir(dir) if fn.endswith('.json')]
samples = [fn for fn in samples if os.path.getsize(fn)]
def ld(fn):
    with open(fn) as f:
        return json.load(f)
db = [ld(fn) for fn in samples]
soc = max(db, key = lambda e: e["t"])["soc"]

target = float(sys.argv[1])

ah = (target - soc)

print(f"Current SOC {soc:.0f}, target {target:.0f}, need {ah:.0f}")

if ah > 0:
    s = int(3600 * abs(ah) / 14)
    assert s > 0
    print(f"Top-up change for: {s/3600:.1f} hours")
    cmd = f"""ssh raspberrypi "curl 'http://192.168.12.31/relay/0?turn=on&timer={s}'" """
    print(cmd)
    # os.system(cmd)
