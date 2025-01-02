import os
import time
import json

dir= "/home/jamesb/tsd/sungauge40"
samples = [dir + "/" + fn for fn in os.listdir(dir) if fn.endswith('.json')]
samples = [fn for fn in samples if os.path.getsize(fn)]
def ld(fn):
    with open(fn) as f:
        return json.load(f)
db = [ld(fn) for fn in samples]
t0 = time.time()
a = [d["current"] for d in db if d["t"] > (t0 - 24*60*60)]
a24 = -(24 * sum(a) / len(a))
if a24 < 0:
    s = int(3600 * abs(a24) / 14)
    assert s > 0
    os.system(f"curl 'http://192.168.12.31/relay/0?turn=on&timer={s}'")
