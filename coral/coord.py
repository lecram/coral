# Copyright (c) 2014 Marcel Rodrigues
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
Spherical Geometry and Polyline simplification.
"""

# http://www.movable-type.co.uk/scripts/latlong.html
# http://williams.best.vwh.net/avform.htm

import math
import itertools

from . import bbox

class Buffer:

    def __init__(self, n):
        assert n & (n - 1) == 0 # n must be a power of two.
        self.n = n
        self.buf = [None] * n
        self.s = self.e = 0
        self._m1 = n - 1
        self._m2 = (n << 1) - 1

    def __str__(self):
        if self.isempty():
            return "<>"
        else:
            i = self.s
            end = self.e
            seq = []
            while i != end:
                seq.append(self.buf[i & self._m1])
                i = self._inc(i)
            return "<{}>".format(" ".join(seq))

    def _inc(self, i):
        return (i + 1) & self._m2

    def _dec(self, i):
        return (i - 1) & self._m2

    def isempty(self):
        return self.e == self.s

    def isfull(self):
        return self.e == self.s ^ self.n

    def push(self, o):
        assert not self.isfull()
        self.buf[self.e & self._m1] = o
        self.e = self._inc(self.e)

    def pop(self):
        assert not self.isempty()
        self.e = self._dec(self.e)
        o = self.buf[self.e & self._m1]
        return o

    def peek(self):
        assert not self.isempty()
        o = self.buf[self._dec(self.e) & self._m1]
        return o

    def shift(self):
        assert not self.isempty()
        o = self.buf[self.s & self._m1]
        self.s = self._inc(self.s)
        return o

def _test_buffer():
    print("Running tests...")
    N = 4
    assert N > 2
    b = Buffer(N)
    assert b.isempty()
    assert not b.isfull()
    b.push(5)
    b.push(7)
    assert not b.isempty()
    assert not b.isfull()
    assert b.pop() == 7
    b.push(11)
    assert b.shift() == 5
    assert b.shift() == 11
    for i in range(23):
        if b.isfull():
            b.shift()
        b.push(i)
    assert not b.isempty()
    assert b.isfull()
    assert b.pop() == 22
    assert b.shift() == 19
    assert b.shift() == 20
    assert b.pop() == 21
    assert b.isempty()
    assert not b.isfull()
    print("OK")

def corangle(a):
    "Correct angle such that `-pi <= a <= pi`."
    while a < -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a

#http://en.wikipedia.org/wiki/Earth_radius#Geocentric_radius
def radiusat(lat, ellipsoid=None):
    if ellipsoid is None:
        ellipsoid = WGS84
    a, b = ellipsoid.a, ellipsoid.b
    radlat = math.radians(lat)
    coslat = math.cos(radlat)
    sinlat = math.sin(radlat)
    acoslatsqr = a * a * coslat * coslat
    bsinlatsqr = b * b * sinlat * sinlat
    num = a * a * acoslatsqr + b * b * bsinlatsqr
    den = acoslatsqr + bsinlatsqr
    radius = math.sqrt(num / den)
    return radius

def haversine(lon1, lat1, lon2, lat2, R=None):
    "Return the distance in meters between two points."
    if R is None:
        R = radiusat((lat1 + lat2) / 2)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a1 = math.sin(dLat / 2) * math.sin(dLat / 2)
    a2 = math.sin(dLon / 2) * math.sin(dLon / 2) * math.cos(lat1) * math.cos(lat2)
    a = a1 + a2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d

def bearing(lon1, lat1, lon2, lat2):
    dLon = math.radians(lon1 - lon2)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    b = math.degrees(math.atan2(y, x))
    return b

def destination(lon, lat, bear, dist, R=None):
    """Given a starting point, a bearing and a distance, return the ending point.
    >>> from coral import coord
    >>> r = 1000
    >>> d = coord.haversine(40, 20, 45, 22, r)
    >>> b = coord.bearing(40, 20, 45, 22)
    >>> coord.destination(40, 20, b, d, r)
    (45.0, 21.999999999999996)
    >>>
    """

    # Everything need to be converted into radians.
    rlon, rlat = math.radians(lon), math.radians(lat)
    tc = math.radians(bear)
    if R is None:
        R = radiusat(lat)
    d = dist / R
    coslat = math.cos(rlat)
    sinlat = math.sin(rlat)
    cosd = math.cos(d)
    sind = math.sin(d)
    costc = math.cos(tc)
    sintc = math.sin(tc)
    lat = math.asin(sinlat*cosd + coslat*sind*costc)
    dlon = math.atan2(sintc*sind*coslat, cosd - sinlat*math.sin(lat))
    lon = corangle(rlon - dlon)
    lon, lat = math.degrees(lon), math.degrees(lat)
    return lon, lat

def midpoint(lon1, lat1, lon2, lat2):
    dlon = math.radians(lon2 - lon1)
    lon1 = math.radians(lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    cosdlon = math.cos(dlon)
    sindlon = math.sin(dlon)
    coslat1 = math.cos(lat1)
    sinlat1 = math.sin(lat1)
    coslat2 = math.cos(lat2)
    sinlat2 = math.sin(lat2)
    bx = coslat2 * cosdlon
    by = coslat2 * sindlon
    lon3 = lon1 + math.atan2(by, coslat1 + bx)
    sqcoslat1bx = (coslat1 + bx) * (coslat1 + bx)
    lat3 = math.atan2(sinlat1 + sinlat2, math.sqrt(sqcoslat1bx + by*by))
    lon3, lat3 = math.degrees(lon3), math.degrees(lat3)
    return lon3, lat3

def geocentroid(region, bb=None, epsilon=None):
    # region is a list of polygons in geographic coordinates.
    if bb is None:
        for poly in region:
            bb = bbox.BBox(poly) | bb
    if epsilon is None:
        epsilon = 1e-10
    c0 = bb.center()
    while True:
        # Should probably use Lambert Azimuthal equal-area instead.
        proj = Stereographic(c0)
        cw = []
        for poly in region:
            xys = [proj.geo2rect(lon, lat) for lon, lat in poly]
            # http://en.wikipedia.org/wiki/Centroid#Centroid_of_polygon
            cx = cy = sa = 0
            for (x0, y0), (x1, y1) in zip(xys, xys[1:] + xys[:1]):
                f = x0 * y1 - x1 * y0
                cx += (x0 + x1) * f
                cy += (y0 + y1) * f
                sa += f
            d = 3 * sa
            cx /= d
            cy /= d
            cw.append(((cx, cy), sa))
        cx = cy = sw = 0
        for (x, y), w in cw:
            cx += x * w
            cy += y * w
            sw += w
        cx /= sw
        cy /= sw
        c1 = proj.rect2geo(cx, cy)
        if abs(c1[0] - c0[0]) <= epsilon and abs(c1[1] - c0[1]) <= epsilon:
            break
        c0 = c1
    return c1

def bearing2cardinal(b):
    cardinals = [
        'N', 'NNW', 'NW', 'WNW',
        'W', 'WSW', 'SW', 'SSW',
        'S', 'SSE', 'SE', 'ESE',
        'E', 'ENE', 'NE', 'NNE'
    ]
    b = (b + 360) % 360
    index = 2 * b / 45
    return cardinals[round(index) % 16]

def bearing2hours(b):
    b = (b + 360) % 360
    return 12 - b / 30

def collinear(a, b, c):
    xa, ya = a
    xb, yb = b
    xc, yc = c
    cln = (xa - xc) * (yb - ya) == (xa - xb) * (yc - ya)
    return cln

def sqr_fit(s, m):
    for x, y in s:
        x = round(x / m)
        y = round(y / m)
        yield (x, y)

def open_no_slit(s, k):
    b = Buffer(k)
    p = next(s)
    yield p
    q = next(s)
    for r in s:
        if r == q:
            continue
        if not collinear(p, q, r):
            if not b.isempty() and q == b.peek():
                b.pop()
            else:
                if b.isfull():
                    yield b.shift()
                b.push(q)
        p, q = q, r
    while not b.isempty():
        yield b.shift()
    yield q

def closed_no_slit(s, k):
    b1 = Buffer(k)
    b2 = Buffer(k)
    p = next(s)
    yield p
    q = next(s)
    for r in s:
        if r == q:
            continue
        if not collinear(p, q, r):
            if not b1.isempty() and q == b1.peek():
                b1.pop()
            else:
                if b1.isfull():
                    t = b1.shift()
                    if b2.isfull():
                        yield t
                    else:
                        b2.push(t)
                b1.push(q)
        p, q = q, r
    while not b1.isempty():
        p = b1.pop()
        q = b2.shift()
        if p != q:
            break
    while not b1.isempty():
        yield b1.shift()
    yield p
    yield q
    while not b2.isempty():
        yield b2.shift()
    yield r

def simplify(xys, scl, closed=False, k=8):
    s = sqr_fit(xys, scl)
    if closed:
        return closed_no_slit(s, k)
    else:
        return open_no_slit(s, k)
