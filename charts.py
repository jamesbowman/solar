import time
import os
import json

import numpy as np
from scipy.ndimage import gaussian_filter
import svgwrite
import cairo
import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

from PIL import Image, ImageDraw, ImageFont, ImageChops

import rt
import sunmoon
from sunalt import solar_elevations
import power

def smooth(ts, h):
    tt = np.array([t for (t,v) in ts]).astype(float)
    vv = np.array([v for (t,v) in ts]).astype(float)
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
    g = np.exp(-(x * x) / (2 * c2)).astype(float)
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

        if ts:
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

    def curve(self):
        ts = [(d["t"], d[self.datum]) for d in self.db()]

        if ts:
            (times, dd) = smooth(ts, 120)

            self.times = times
            self.dd = dd

            self.d0 = min(self.dmin, min(dd))
            self.d1 = max(self.dmax, max(dd))
            self.t0 = min(times)
            self.t1 = max(times)

            poly = self.points()
            return poly

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

if 0:
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

# class Solar_V(Draw, Renogy_Curve):
#     title = "Solar Voltage (V)"
#     dir = TSDS + "renogy"
#     datum = "Solar Voltage"
#     svgname = "graph_c.svg"
#     dmin = 6
#     dmax = 30

class Grid(Draw, Curve):
    def db(self):
        return power.powerlog()
    datum = "power"
    title = "Grid Use (W)"
    svgname = "graph_d.svg"
    dmin = 0
    dmax = 800

class Main_V(Draw, Renogy_Curve):
    title = "Main Battery (V)"
    datum = "Battery Voltage"
    svgname = "graph_e.svg"
    dmin = 11.8
    dmax = 14.7

class main_SOC(Draw, Renogy_Curve):
    title = "Main SOC (%)"
    dir = TSDS + "renogy"
    datum = "SOC"
    svgname = "graph_f.svg"
    dmin = 6
    dmax = 30
    def strvalue(self, d):
        return f"{d:.0f}"

class Coop_V(Draw, Curve):
    title = "Coop Battery (V)"
    dir = TSDS + "coop"
    datum = "vbatt"
    svgname = "graph_i.svg"
    dmin = 11
    dmax = 15

class Coop_Temp(Draw, Curve):
    title = "Coop (°C)"
    dir = TSDS + "coop"
    datum = "temp"
    svgname = "graph_j.svg"
    dmin = 6
    dmax = 30

if 1:
    class Coop_Door(Draw, Curve):
        title = "Coop Door"
        dir = TSDS + "coop"
        datum = "dooropen"
        svgname = "graph_h.svg"
        dmin = 0
        dmax = 1

class Main_Temp(Draw, Renogy_Curve):
    title = "Shed (°C)"
    dir = TSDS + "renogy"
    datum = "Battery Temperature"
    svgname = "graph_k.svg"
    dmin = 6
    dmax = 30

# class Controller_Temp(Draw, Curve):
#     title = "Controller (°C)"
#     dir = TSDS + "renogy"
#     datum = "Controller Temperature"
#     svgname = "graph_k.svg"
#     dmin = 6
#     dmax = 30

class Upstairs_Temp(Draw, Curve):
    title = "Upstairs (°C)"
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
        for i,k in enumerate(("dawn", "dusk")):
            y = 200 + 50 * i
            dwg.add(dwg.text(k, insert=(140, y), font_family="Helvetica", font_size="26pt"))
            v = s[k].strftime("%H:%M")
            dwg.add(dwg.text(v, insert=(280, y), font_family="Helvetica", font_size="26pt"))
            
        dwg.save()

class CairoSurface:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = cairo.Context(self.surface)

    def asarray(self):
        r = np.ndarray(shape=(self.height, self.width, 4), dtype=np.uint8, buffer=self.surface.get_data())
        return r[:, :, :3] / 255

def gauss(ni, sigma):
    filtered_r = gaussian_filter(ni[:, :, 0], sigma=sigma)
    filtered_g = gaussian_filter(ni[:, :, 1], sigma=sigma)
    filtered_b = gaussian_filter(ni[:, :, 2], sigma=sigma)
    return np.stack([filtered_r, filtered_g, filtered_b], axis=2)

class Silly(Curve):
    title = "Upstairs (°C)"
    dir = TSDS + "bedroom"
    datum = "temp"
    dmin = 6
    dmax = 30

    def __init__(self):
        
        # Set up the image dimensions
        width, height = 480, 360

        surface = CairoSurface(width, height)
        ctx = surface.ctx

        ctx.set_source_rgb(1, 1, 1)  # White
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(5)

        cc = self.curve()
        ctx.move_to(*cc[0])
        for p in cc[1:]:
            ctx.line_to(*p)
        ctx.stroke()

        labels = []
        dd = self.dd
        for (yo,dpt) in [(.2,min(dd)), (-.3,max(dd))]:
            L = list(dd)
            i = len(L) - L[::-1].index(dpt) - 1
            (x, y) = self.gpoint(self.times[i], dd[i])
            # dwg.add(dwg.circle((x, y), r=3, **args))
            print(x, y)
            ctx.arc(x, y, 6, 0, 2 * 3.14159)
            ctx.fill()
            s = self.strvalue(dpt)
            # dwg.add(dwg.text(s, insert=(x, y+100*yo), font_family="Helvetica", font_size="26pt", text_anchor = "middle"))
            labels.append((s, x, y+100*yo))

        l_line = surface.asarray()

        surface = CairoSurface(width, height)
        ctx = surface.ctx


        sa = solar_elevations()

        ctx.set_line_width(3)
        for (i, e) in enumerate(sa):
            x = rescale(i, 0, len(sa), X0, X1)
            y = Y0
            print(x, y)
            if e > 10:
                ctx.set_source_rgb(0, rescale(e, 0, 45, .3, 1), 1)
                # ctx.arc(x, y, 20, 0, 2 * 3.14159)
                ctx.move_to(x, Y0)
                ctx.line_to(x, Y1)
                ctx.stroke()

        l_sunalt = gauss(surface.asarray() * 0.3, 6)

        if 1:
            fn = "IBMPlexSans-Medium.otf"
            im = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(im)
            font = ImageFont.truetype(fn, 40)

            text = self.title
            def center(s, x, y, font):
                bbox = draw.textbbox((0, 0), s, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = x - (text_width) / 2
                y = y - (text_height) / 2

                # Draw text onto the image (0 for black text)
                draw.text((x, y), s, fill=(255,255,255), font=font)

            center(self.title, width / 2, 50, font)
            font = ImageFont.truetype(fn, 20)
            for (s, x, y) in labels:
                center(s, x, y, font)

            l_text = np.array(im) / 255

        l_bg = rt.glow()

        l_glow = gaussian_filter(l_text + l_line, sigma=12)

        final = (1.0 * l_bg +
                 1.0 * l_sunalt +
                 0.4 * l_glow +
                 0.7 * l_text +
                 0.7 * l_line 
                 )
        final = np.minimum(255, np.maximum(final * 255, 0)).astype(np.uint8)
        Image.fromarray(final).save('out.png')

if __name__ == "__main__":
    # [(print(c), c()) for c in Draw.__subclasses__()]
    Silly()
