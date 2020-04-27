import datetime
import time
import svgwrite
import numpy as np
from scipy.ndimage import gaussian_filter1d

def rescale(x, x0, x1, y0 = 0, y1 = 1):
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)
(X0, Y0, X1, Y1) = (15, 350, 590, 5)

def ongraph(x, y):
    return (rescale(x, 0, 1, X0, X1), rescale(y, 0, 1, Y0, Y1))

class Curve:
    def __init__(self, times, dd, d0, d1):
        self.times = times
        self.dd = list(gaussian_filter1d(np.array(dd), 3))
        self.latest = dd[-1]
        self.d0 = d0
        self.d1 = d1

    def plot_latest(self, dwg, fmt):
        s = fmt.format(self.latest)
        y = rescale(self.latest, self.d0, self.d1)
        dwg.add(dwg.text(s, insert=ongraph(1.01, y), font_family="Arial", text_anchor = "start", dominant_baseline = "middle"))

    def gpoint(self, d):
        return rescale(d, self.d0, self.d1, Y0, Y1)

    def points(self):
        return [(t, self.gpoint(d)) for (t, d) in zip(self.times, self.dd)]
        
def redraw(datums):
    dwg = svgwrite.Drawing("graph.svg", size=(650, 400))

    cutoff = time.time() - (18 * 3600)
    (times, soc, vb, pi) = [[d[i] for d in datums if d[0] > cutoff] for i in range(4)]
    t0 = min(times)
    t1 = max(times)
    gtimes = [rescale(t, t0, t1, X0, X1) for t in times]

    t0m = ((int(t0) + 3599) // 3600) * 3600
    for t in range(t0m, t1, 3600):
        ti = datetime.datetime.fromtimestamp(t)
        hhmm = "%02d:%02d" % (ti.hour, ti.minute)
        x = rescale(t, t0, t1)
        dwg.add(dwg.line(ongraph(x, -.01), ongraph(x, 0), stroke="black", stroke_width=".5"))
        dwg.add(dwg.text(hhmm, insert=ongraph(x, -.04), font_family="Arial", font_size="7pt", text_anchor = "middle"))

    args = {'fill':'black', 'stroke':'black', 'fill_opacity':0.2, 'stroke_width':1}
    c = Curve(gtimes, vb, 10.8, 14.7)
    poly = [ongraph(0,0)] + c.points() + [ongraph(1,0)]
    dwg.add(dwg.polygon(poly, **args))
    c.plot_latest(dwg, "{:.1f} V")

    args = {'stroke':'black', 'fill_opacity':0.0, 'stroke_width':2}
    c = Curve(gtimes, pi, 0, 600)
    dwg.add(dwg.polyline(c.points(), **args))
    c.plot_latest(dwg, "{:.0f} W")

    dwg.save()

if __name__ == "__main__":
    db = [eval(l) for l in open("log")]
    redraw(db)
