import numpy as np

def smooth(ts, h):
    tt = np.array([t for (t,v) in ts])
    vv = np.array([v for (t,v) in ts])
    # return (tt, vv)
    t0 = min(tt)
    td = max(tt) - t0
    tt = (tt - t0) / td
    w = len(tt)
    sh = (h, w)
    d = np.tile(tt, h).reshape(sh)
    adj = (np.repeat(np.arange(0, h), w) / (h - 1)).reshape(sh)
    # print(d)
    # print(adj)
    # print(d - adj)

    x = d - adj
    c2 = 9e-6
    g = np.exp(-(x * x) / (2 * c2))
    v = np.tile(vv, h).reshape(sh)
    vg = v * g
    r = vg.sum(1) / g.sum(1)
    return (np.linspace(t0, t0 + td, h), r)
