from PIL import Image
import numpy as np
import time
import numbers

class vec3():
    def __init__(self, x, y, z):
        (self.x, self.y, self.z) = (x, y, z)
    def __mul__(self, other):
        return vec3(self.x * other, self.y * other, self.z * other)
    def __add__(self, other):
        return vec3(self.x + other.x, self.y + other.y, self.z + other.z)
    def __sub__(self, other):
        return vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    def dot(self, other):
        return (self.x * other.x) + (self.y * other.y) + (self.z * other.z)
    def __abs__(self):
        return self.dot(self)
    def norm(self):
        mag = np.sqrt(abs(self))
        return self * (1.0 / np.where(mag == 0, 1, mag))
    def components(self):
        return (self.x, self.y, self.z)
rgb = vec3

def gaussian(x, mu, sigma):
    """
    Gaussian function.
    :param x: array-like, points at which to evaluate the function
    :param mu: mean of the distribution
    :param sigma: standard deviation of the distribution
    :return: array-like, values of the Gaussian function at the given points x
    """
    factor1 = 1 / (sigma * np.sqrt(2 * np.pi))
    factor2 = np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    return factor1 * factor2

def u8(a):
    # return (255 * a).astype(np.uint8)
    return (np.minimum(1, np.maximum(a, 0)) * 255).astype(np.uint8)

def glow(sigma):
    (w, h) = (480, 360)

    x = np.tile(np.linspace(-1, 1, w), h)
    a = h / w
    y = np.repeat(np.linspace(-a, a, h), w)

    d = np.sqrt((x*x) + (y*y))
    # g = np.where(d < .5, 1, 0)
    g = gaussian(d, 0, sigma)
    g /= max(g)

    YELLOW = rgb(0.5, 0.9, 1.0)
    GRN = rgb(0.5, 0.7, 0.5)
    bg = GRN * g.reshape(h, w) * 0.6
    bg = rgb(1,1,1) * g.reshape(h, w)
    return np.stack(bg.components(), axis=-1)
    bgc = tuple((u8(c) for c in bg.components()))
    rgba_array = np.stack(bgc, axis=-1)
    return rgba_array
