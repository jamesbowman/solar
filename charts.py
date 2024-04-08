import sys
import time
import math
import os
import json

import numpy as np
from scipy.ndimage import gaussian_filter
import cairo

from PIL import Image, ImageDraw, ImageFont, ImageChops

import rt
import sunmoon
from sunalt import solar_elevations
import power

def smooth(ts, h, t0, t1):
    tt = np.array([t for (t,v) in ts]).astype(float)
    vv = np.array([v for (t,v) in ts]).astype(float)
    td = t1 - t0
    # tt = (tt / (max(tt) - min(tt))) - min(tt)
    tt = (tt - t0) / td
    w = len(tt)
    sh = (h, w)
    print(f"{sh=}")
    d = np.tile(tt, h).reshape(sh)
    adj = (np.repeat(np.arange(0, h), w) / (h - 1)).reshape(sh)
    print(adj)

    x = d - adj
    c2 = 2e-4
    g = np.exp(-(x * x) / (2 * c2)).astype(float)
    v = np.tile(vv, h).reshape(sh)
    vg = v * g
    r = vg.sum(1) / g.sum(1)
    print(np.linspace(t0, t0 + td, h).shape)
    return (np.linspace(t0, t0 + td, h), r)

def smooth(ts, h, t0, t1):
    tt = np.array([t for (t,v) in ts]).astype(float)
    vv = np.array([v for (t,v) in ts]).astype(float)

    w = len(ts)
    sh = (h, w)

    tt_x = np.tile(tt, h).reshape(sh)
    vv_x = np.tile(vv, h).reshape(sh)

    tt_y = (np.repeat(np.linspace(t0, t1, h), w)).reshape(sh)

    delta = np.abs(tt_x - tt_y)
    x = delta / h
    c2 = 70
    g = np.exp(-(x * x) / (2 * c2)).astype(float)

    vg = vv_x * g

    contrib = g.sum(1)

    quality = np.minimum(1.0, np.amax(g, 1) / 4e-3)
    if 0:
        np.set_printoptions(precision=2)
        print(f"{sh=}")
        print(f"{tt_x=}")
        print(f"{tt_y=}")
        print("quality", "min", min(quality.flatten()), max(quality.flatten()))
        print(f"{quality=}")

    r = np.where(contrib, vg.sum(1) / contrib, 0.0)
    return (np.linspace(t0, t1, h), quality, r)


def rescale(x, x0, x1, y0 = 0, y1 = 1):
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)
ap = 80
(X0, Y0, X1, Y1) = (ap, 260, 480-ap, 155)

def ongraph(x, y):
    return (rescale(x, 0, 1, X0, X1), rescale(y, 0, 1, Y0, Y1))

class Curve:
    def gpoint(self, t, q, d):
        return (q,
                rescale(t, self.t0, self.t1, X0, X1),
                rescale(d, self.d0, self.d1, Y0, Y1))

    def points(self):
        return [(self.gpoint(t, q, d)) for (t, q, d) in zip(self.times, self.quality, self.dd)]

    dmin = 999e9
    dmax = -999e9

    def ts(self, d):
        return d["t"]

    def get_datum(self, d):
        return d[self.datum]

    def db(self):
        t0 = time.time()
        samples = [self.dir + "/" + fn for fn in os.listdir(self.dir) if fn.endswith('.json')]
        samples = [fn for fn in samples if os.path.getsize(fn)]
        def ld(fn):
            with open(fn) as f:
                return json.load(f)
        db = [ld(fn) for fn in samples]
        return [d for d in db if self.ts(d) > (t0 - 24*60*60)]

    def curve(self):
        ts = [(self.ts(d), self.get_datum(d)) for d in self.db()]

        if ts:
            t0 = time.time()
            self.t0 = t0 - 24*60*60
            self.t1 = t0

            (times, quality, dd) = smooth(ts, 120, self.t0, self.t1)

            self.times = times
            self.quality = quality
            self.dd = dd

            valid = self.valid()

            self.d0 = min(self.dmin, min(valid))
            self.d1 = max(self.dmax, max(valid))

            poly = self.points()
            return poly
        else:
            self.times = []
            self.quality = []
            self.dd = []


    def valid(self):
        vq = zip(self.dd, self.quality)
        return [v for (v,q) in vq if q > 0.5]

    def strvalue(self, d):
        return f"{d:.1f}"

TSDS = "/home/jamesb/tsd/"

if 1:
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

def sunalt():
    (width, height) = (480, 360)
    surface = CairoSurface(width, height)
    ctx = surface.ctx

    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    sa = solar_elevations()

    ctx.set_line_width(3)
    for (i, e) in enumerate(sa):
        x = rescale(i, 0, len(sa), X0, X1)
        y = Y0
        if e > 0:
            ctx.set_source_rgb(0, rescale(e, 0, 45, .3, 1), 1)
        else:
            ctx.set_source_rgb(1, 0, 0)
        ctx.move_to(x, 0)
        ctx.line_to(x, height)
        ctx.stroke()

    return gauss(surface.asarray(), 10)

l_sunalt = (0.3 * sunalt() * rt.glow(.4))

fn = "IBMPlexSans-Medium.otf"
font1 = ImageFont.truetype(fn, 34)
font2 = ImageFont.truetype(fn, 20)

def center(draw, s, x, y, font):
    bbox = draw.textbbox((0, 0), s, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = x - (text_width) / 2
    y = y - (text_height) / 2

    draw.text((x, y), s, fill=(255,255,255), font=font)

class Tile:

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
        labels = []
        if cc:
            for (p0,p1) in zip(cc, cc[1:]):
                (_, x, y) = p0
                ctx.move_to(x, y)
                (q, x, y) = p1
                ctx.set_line_width(5 * q)
                ctx.line_to(x, y)
                ctx.stroke()

            dd = self.dd
            if not any(np.isnan(dd)):
                valid = self.valid()
                if valid:
                    mn = min(valid)
                    mx = max(valid)
                    annotate = [(-.3, mx)]
                    if mn != mx:
                        annotate += [(.2, mn)]
                    for (yo, dpt) in annotate:
                        L = list(dd)
                        i = len(L) - L[::-1].index(dpt) - 1
                        (q, x, y) = self.gpoint(self.times[i], 1.0, dd[i])
                        # dwg.add(dwg.circle((x, y), r=3, **args))
                        ctx.arc(x, y, 6, 0, 2 * 3.14159)
                        ctx.fill()
                        s = self.strvalue(dpt)
                        # dwg.add(dwg.text(s, insert=(x, y+100*yo), font_family="Helvetica", font_size="26pt", text_anchor = "middle"))
                        labels.append((s, x, y+100*yo))

        l_line = surface.asarray()


        if 1:
            im = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(im)

            center(draw, self.title, width / 2, 50, font1)
            center(draw, self.subtitle(), width / 2, 90, font2)
            for (s, x, y) in labels:
                center(draw, s, x, y, font2)

            l_text = np.array(im) / 255

        l_glow = gaussian_filter(l_text + l_line, sigma=12)

        final = (
                 l_sunalt +
                 0.5 * l_glow +
                 1.0 * l_text +
                 1.0 * l_line 
                 )
        final = np.minimum(255, np.maximum(final * 255, 0)).astype(np.uint8)
        self.im = Image.fromarray(final)

    def subtitle(self):
        return ""

class ReportMJ:
    def subtitle(self):
        avg_w = np.mean(self.valid())
        mj = 24 * 3600 * avg_w / 1e6
        return f"{mj:.1f} MJ"

class Main_Power(ReportMJ, Tile, Renogy_Curve):
    title = "Solar Power (W)"
    dir = TSDS + "renogy"
    datum = "Solar Power"
    pos = (1, 0)
    dmin = 0
    dmax = 200
    def strvalue(self, d):
        return f"{d:.0f}"

class Inverter(ReportMJ, Tile, Curve):
    title = "Inverter (W)"
    dir = TSDS + "shelly30"
    pos = (2, 0)
    def ts(self, d):
        return d["sys"]["unixtime"]
    def get_datum(self, d):
        return d["switch:0"]["apower"]
    dmin = 0
    dmax = 200

class Grid(ReportMJ, Tile, Curve):
    def db(self):
        return power.powerlog()
    datum = "power"
    title = "Grid Use (W)"
    pos = (3, 0)
    dmin = 0
    dmax = 200

class Main_V(Tile, Renogy_Curve):
    title = "Main Battery (V)"
    datum = "Battery Voltage"
    pos = (0, 1)
    dmin = 11.8
    dmax = 14.7

class main_SOC(Tile, Renogy_Curve):
    title = "Main SOC (%)"
    dir = TSDS + "renogy"
    datum = "SOC"
    pos = (1, 1)
    dmin = 40
    dmax = 100
    def strvalue(self, d):
        return f"{d:.0f}"

class Coop_V(Tile, Curve):
    title = "Coop Battery (V)"
    dir = TSDS + "coop"
    datum = "vbatt"
    svgname = "graph_i.svg"
    pos = (0, 2)
    dmin = 11
    dmax = 15

class Coop_Temp(Tile, Curve):
    title = "Coop (°C)"
    dir = TSDS + "coop"
    datum = "temp"
    pos = (1, 2)
    dmin = 6
    dmax = 30

class Coop_Door(Tile, Curve):
    title = "Coop Door"
    dir = TSDS + "coop"
    datum = "dooropen"
    pos = (3, 1)
    dmin = 0
    dmax = 1
    def strvalue(self, d):
        return ["closed", "open"][int(round(d))]

class Main_Temp(Tile, Renogy_Curve):
    title = "Shed (°C)"
    dir = TSDS + "renogy"
    datum = "Battery Temperature"
    pos = (2,2)
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

class Upstairs_Temp(Tile, Curve):
    title = "Upstairs (°C)"
    dir = TSDS + "bedroom"
    datum = "temp"
    svgname = "graph_l.svg"
    pos = (3, 2)
    dmin = 6
    dmax = 30

class Pressure(Tile, Curve):
    title = "Pressure (hPa)"
    dir = TSDS + "bedroom"
    datum = "pressure"
    pos = (2, 1)
    dmin = 1010
    dmax = 1030
    def strvalue(self, d):
        return f"{d:.0f}"

class TimeStamp(Tile):
    pos = (0, 0)
    def __init__(self):
        (width, height) = (480, 360)
        im = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(im)

        s = time.strftime("%H:%M %Z", time.localtime())
        center(draw, s, width / 2, 50, font1)

        s = sunmoon.sun()
        for i,k in enumerate(("dawn", "dusk")):
            y = 150 + 50 * i
            center(draw, k, 240 - 100, y, font1)
            v = s[k].strftime("%H:%M")
            center(draw, v, 240 + 100, y, font1)
        l_text = np.array(im) / 255

        l_glow = gaussian_filter(l_text, sigma=12)

        final = (0.2 * np.array((.0, .3, 1)) * rt.glow(0.45) +
                 0.5 * l_glow +
                 1.0 * l_text
                 )
        final = np.minimum(255, np.maximum(final * 255, 0)).astype(np.uint8)
        self.im = Image.fromarray(final)

if __name__ == "__main__":
    if 0:
        x = Inverter()
        x.im.save("out.png")
        sys.exit(0)

    final = Image.new("RGB", (1920, 1080))
    tiles = [tc() for tc in Tile.__subclasses__()]
    for t in tiles:
        final.paste(t.im, (480 * t.pos[0], 360 * t.pos[1]))
    final.save("out.png")
