import time
import os
import json

import numpy as np
import svgwrite

import sunmoon

def smooth(ts, h):
    tt = np.array([t for (t,v) in ts]).astype(np.float)
    vv = np.array([v for (t,v) in ts]).astype(np.float)
    t0 = min(tt)
    td = max(tt) - t0
    # tt = (tt / (max(tt) - min(tt))) - min(tt)
    tt = (tt - t0) / td
    w = len(tt)
    sh = (h, w)
    d = np.tile(tt, h).reshape(sh)
    adj = (np.repeat(np.arange(0, h), w) / (h - 1)).reshape(sh)

    x = d - adj
    c2 = 2e-4
    g = np.exp(-(x * x) / (2 * c2)).astype(np.float)
    v = np.tile(vv, h).reshape(sh)
    vg = v * g
    r = vg.sum(1) / g.sum(1)
    return (np.linspace(t0, t0 + td, h), r)

def rescale(x, x0, x1, y0 = 0, y1 = 1):
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)
ap = 80
(X0, Y0, X1, Y1) = (ap, 260, 480-ap, 155)

def ongraph(x, y):
    return (rescale(x, 0, 1, X0, X1), rescale(y, 0, 1, Y0, Y1))

class Blank:
    def __init__(self):
        dwg = svgwrite.Drawing(self.svgname, size=(480, 360))
        dwg.save()

class Curve:
    def gpoint(self, t, d):
        return (rescale(t, self.t0, self.t1, X0, X1),
                rescale(d, self.d0, self.d1, Y0, Y1))

    def points(self):
        return [(self.gpoint(t, d)) for (t, d) in zip(self.times, self.dd)]

    dmin = 999e9
    dmax = -999e9

    def db(self):
        t0 = time.time()
        samples = [self.dir + "/" + fn for fn in os.listdir(self.dir) if fn.endswith('.json')]
        def ld(fn):
            with open(fn) as f:
                return json.load(f)
        db = [ld(fn) for fn in samples]
        return [d for d in db if d["t"] > (t0 - 24*60*60)]

    def __init__(self):
        dwg = svgwrite.Drawing(self.svgname, size=(480, 360))
        dwg.add(dwg.text(self.title, insert=(240, 70), font_family="Helvetica", font_size="33pt", text_anchor = "middle"))

        ts = [(d["t"], d[self.datum]) for d in self.db()]

        (times, dd) = smooth(ts, 120)

        self.times = times
        self.dd = dd

        self.d0 = min(self.dmin, min(dd))
        self.d1 = max(self.dmax, max(dd))
        self.t0 = min(times)
        self.t1 = max(times)

        poly = self.points()
        args = {'stroke':'black', 'fill_opacity':0.0, 'stroke_width':6}
        dwg.add(dwg.polyline(poly, **args))

        dd = self.dd
        for (yo,dpt) in [(.5,min(dd)), (-.2,max(dd))]:
            L = list(dd)
            i = len(L) - L[::-1].index(dpt) - 1
            (x, y) = self.gpoint(self.times[i], dd[i])
            dwg.add(dwg.circle((x, y), r=3, **args))
            s = self.strvalue(dpt)
            dwg.add(dwg.text(s, insert=(x, y+100*yo), font_family="Helvetica", font_size="26pt", text_anchor = "middle"))
        dwg.save()

    def strvalue(self, d):
        return f"{d:.1f}"

"""
a b c d
e f g h
i j k l
"""
class Draw:
    pass

class BlankA(Draw, Blank): svgname = "graph_a.svg"
class BlankB(Draw, Blank): svgname = "graph_b.svg"
class BlankC(Draw, Blank): svgname = "graph_c.svg"
class BlankD(Draw, Blank): svgname = "graph_d.svg"

class BlankE(Draw, Blank): svgname = "graph_e.svg"
class BlankF(Draw, Blank): svgname = "graph_f.svg"
class BlankG(Draw, Blank): svgname = "graph_g.svg"
class BlankH(Draw, Blank): svgname = "graph_h.svg"

class BlankI(Draw, Blank): svgname = "graph_i.svg"
class BlankJ(Draw, Blank): svgname = "graph_j.svg"
class BlankK(Draw, Blank): svgname = "graph_k.svg"
class Blankl(Draw, Blank): svgname = "graph_l.svg"

TSDS = "/home/jamesb/tsd/"

def db_renogy():
    t0 = time.time()
    samples = [TSDS + "/renogy/" + fn for fn in os.listdir(TSDS + "/renogy/") if fn.endswith('.json')]
    def ld(fn):
        with open(fn) as f:
            return json.load(f)
    db = [ld(fn) for fn in samples]
    return [d for d in db if d["t"] > (t0 - 24*60*60)]
DB_RENOGY = db_renogy()

class Renogy_Curve(Curve):
    def db(self):
        return DB_RENOGY

class Main_Power(Draw, Renogy_Curve):
    title = "Solar Power (W)"
    dir = TSDS + "renogy"
    datum = "Solar Power"
    svgname = "graph_b.svg"
    dmin = 0
    dmax = 400
    def strvalue(self, d):
        return f"{d:.0f}"

class Solar_V(Draw, Renogy_Curve):
    title = "Solar Voltage (V)"
    dir = TSDS + "renogy"
    datum = "Solar Voltage"
    svgname = "graph_c.svg"
    dmin = 6
    dmax = 30

class Main_V(Draw, Renogy_Curve):
    title = "Battery Voltage (V)"
    datum = "Battery Voltage"
    svgname = "graph_e.svg"
    dmin = 11.8
    dmax = 14.7

class main_SOC(Draw, Renogy_Curve):
    title = "Battery SOC (%)"
    dir = TSDS + "renogy"
    datum = "SOC"
    svgname = "graph_f.svg"
    dmin = 6
    dmax = 30
    def strvalue(self, d):
        return f"{d:.0f}"

class Coop_Temp(Draw, Curve):
    title = "Coop (°C)"
    dir = TSDS + "coop"
    datum = "temp"
    svgname = "graph_i.svg"
    dmin = 6
    dmax = 30

class Main_Temp(Draw, Renogy_Curve):
    title = "Battery (°C)"
    dir = TSDS + "renogy"
    datum = "Battery Temperature"
    svgname = "graph_j.svg"
    dmin = 6
    dmax = 30

class Controller_Temp(Draw, Curve):
    title = "Controller (°C)"
    dir = TSDS + "renogy"
    datum = "Controller Temperature"
    svgname = "graph_k.svg"
    dmin = 6
    dmax = 30

class Bedroom_Temp(Draw, Curve):
    title = "Bedroom (°C)"
    dir = TSDS + "bedroom"
    datum = "temp"
    svgname = "graph_l.svg"
    dmin = 6
    dmax = 30


class TimeStamp(Draw):
    svgname = "graph_a.svg"
    def __init__(self):
        dwg = svgwrite.Drawing(self.svgname, size=(480, 360))
        s = time.strftime("%H:%M %Z", time.localtime())
        dwg.add(dwg.text(s, insert=(240, 100), font_family="Helvetica", font_size="50pt", text_anchor = "middle"))
        s = sunmoon.sun()
        for i,k in enumerate(("sunrise", "sunset")):
            y = 200 + 50 * i
            dwg.add(dwg.text(k, insert=(140, y), font_family="Helvetica", font_size="26pt"))
            v = s[k].strftime("%H:%M")
            dwg.add(dwg.text(v, insert=(280, y), font_family="Helvetica", font_size="26pt"))
            
        dwg.save()

if __name__ == "__main__":
    [c() for c in Draw.__subclasses__()]
