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
Map projections.
"""

import math
import collections

from . import coord

corangle = coord.corangle

class ProjectionError(Exception): pass

# See http://www.epsg-registry.org/ for datums.

# a = equatorial radius (meters)
# b = polar radius (meters)
# e = eccentricity
# f = flattening
Ellipsoid = collections.namedtuple("Row", "a b e f")

# http://en.wikipedia.org/wiki/World_Geodetic_System
a = 6378137
f = 1 / 298.257223563
WGS84 = Ellipsoid(
  a,
  a * (1 - f),              # b = 6356752.314245179
  math.sqrt(2 * f - f * f), # e = 0.08181919084262149
  f
)

# http://en.wikipedia.org/wiki/GRS_80
a = 6378137
f = 1 / 298.257222101
GRS80 = Ellipsoid(
  a,
  a * (1 - f),              # b = 6356752.314140356
  math.sqrt(2 * f - f * f), # e = 0.08181919104281579
  f
)
del a, f

class Proj:

    def __init__(self, origin=None, radius=None):
        if origin is None:
            lon0, lat0 = 0, 0
        else:
            lon0, lat0 = origin
        self.lon0, self.lat0 = math.radians(lon0), math.radians(lat0)
        if radius is None:
            self.r = (WGS84.a + WGS84.b) / 2
        else:
            self.r = radius

class EProj:

    def __init__(self, origin=None, ellipsoid=None):
        if origin is None:
            lon0, lat0 = 0, 0
        else:
            lon0, lat0 = origin
        self.lon0, self.lat0 = math.radians(lon0), math.radians(lat0)
        if ellipsoid is None:
            self.ellipsoid = WGS84
        else:
            self.ellipsoid = ellipsoid
        self.a, self.b, self.e, self.f = self.ellipsoid

class Mercator(Proj):
    "Mercator Projection for the Spherical Earth."

    def geo2rect(self, lon, lat):
        if lat == -90:
            raise ProjectionError("Invalid latitude for this projection: {}.".format(lat))
        lon, lat = math.radians(lon), math.radians(lat)
        x = self.r * corangle(lon - self.lon0)
        y = self.r * math.log(math.tan(math.pi / 4 + lat / 2))
        return x, y

    def rect2geo(self, x, y):
        lon = corangle(x / self.r + self.lon0)
        lat = math.atan(math.sinh(y / self.r))
        lon, lat = math.degrees(lon), math.degrees(lat)
        return lon, lat

    def scale(self, lon, lat):
        lat = math.radians(lat)
        k = 1 / math.cos(lat)
        return k

class EMercator(EProj):
    "Mercator Projection for the Ellipsiod Earth."

    def geo2rect(self, lon, lat):
        if lat == -90:
            raise ProjectionError("Invalid latitude for this projection: {}.".format(lat))
        lon, lat = math.radians(lon), math.radians(lat)
        x = self.a * corangle(lon - self.lon0)
        esinlat = self.e * math.sin(lat)
        y = math.tan(math.pi / 4 + lat / 2)
        y *= ((1 - esinlat) / (1 + esinlat)) ** (self.e / 2)
        # FIXME:
        #  if lat == -90, ValueError is raised due to math.log(0.0)
        y = self.a * math.log(y)
        return x, y

    def rect2geo(self, x, y):
        lon = corangle(x / self.a + self.lon0)
        t = math.exp(-y / self.a)
        l0 = math.pi / 2 - 2 * math.atan(t)
        ok = False
        while not ok:
            esinlat = self.e * math.sin(l0)
            lat = t * ((1 - esinlat) / (1 + esinlat)) ** (self.e / 2)
            lat = math.pi / 2 - 2 * math.atan(lat)
            ok = lat == l0
            l0 = lat
        lon, lat = math.degrees(lon), math.degrees(lat)
        return lon, lat

    def scale(self, lon, lat):
        lat = math.radians(lat)
        sinlat = math.sin(lat)
        coslat = math.cos(lat)
        k = math.sqrt(1 - self.e * self.e * sinlat * sinlat) / coslat
        return k

class TransMercator(Proj):
    "Transverse Mercator Projection for the Spherical Earth."

    def geo2rect(self, lon, lat):
        lon, lat = math.radians(lon), math.radians(lat)
        b = math.cos(lat) * math.sin(lon - self.lon0)
        if b in (-1, 1):
            lon, lat = math.degrees(lon), math.degrees(lat)
            raise ProjectionError("Invalid coordinates for this projection: {}, {}.".format(lon, lat))
        x = self.r * math.atanh(b)
        y = self.r * corangle(math.atan2(math.tan(lat), math.cos(lon - self.lon0)) - self.lat0)
        return x, y

    def rect2geo(self, x, y):
        d = y / self.r + self.lat0
        lon = self.lon0 + math.atan2(math.sinh(x / self.r), math.cos(d))
        lat = math.asin(math.sin(d) / math.cosh(x / self.r))
        lon, lat = math.degrees(lon), math.degrees(lat)
        return lon, lat

    def scale(self, lon, lat):
        lon, lat = math.radians(lon), math.radians(lat)
        b = math.cos(lat) * math.sin(lon - self.lon0)
        k = 1 / math.sqrt(1 - b * b)
        return k

class ObliqMercator(Proj):
    "Oblique Mercator Projection for the Spherical Earth."

    def geo2rect(self, lon, lat):
        lon, lat = math.radians(lon), math.radians(lat)
        c, s = math.cos(self.lat0), math.sin(self.lat0)
        a = s * math.sin(lat) - c * math.cos(lat) * math.sin(lon - self.lon0)
        v = math.tan(lat) * c + s * math.sin(lon - self.lon0)
        h = math.cos(lon - self.lon0)
        x = self.r * math.atan(v / h)
        y = self.r * math.atanh(a)
        return x, y

    def rect2geo(self, x, y):
        c, s = math.cos(self.lat0), math.sin(self.lat0)
        xr, yr = x / self.r, y / self.r
        lat = math.asin(s * math.tanh(yr) + c * math.sin(xr) / math.cosh(yr))
        v = s * math.sin(xr) - c * math.sinh(yr)
        h = math.cos(xr)
        lon = self.lon0 + math.atan(v / h)
        lon, lat = math.degrees(lon), math.degrees(lat)
        return lon, lat

    def scale(self, lon, lat):
        lon, lat = math.radians(lon), math.radians(lat)
        c, s = math.cos(self.lat0), math.sin(self.lat0)
        a = s * math.sin(lat) - c * math.cos(lat) * math.sin(lon - self.lon0)
        k = 1 / math.sqrt(1 - a * a)
        return k

class EckertIV(Proj):
    "Eckert IV Projection for the Spherical Earth."

    CX = 2 / math.sqrt(4 * math.pi + math.pi * math.pi)
    CY = 2 * math.sqrt(math.pi / (4 + math.pi))
    C = 2 + math.pi / 2

    def geo2rect(self, lon, lat):
        lon, lat = math.radians(lon), math.radians(lat)
        theta = lat / 2
        sinlat = math.sin(lat)
        delta = 1
        while abs(delta) > 1e-6:
            costheta = math.cos(theta)
            sintheta = math.sin(theta)
            num = theta + sintheta * costheta + 2 * sintheta - self.C * sinlat
            den = 2 * costheta * (1 + costheta)
            delta = - num / den
            theta += delta
        x = self.CX * self.r * corangle(lon - self.lon0) * (1 + costheta)
        y = self.CY * self.r * sintheta
        return x, y

    def rect2geo(self, x, y):
        theta = math.asin(y / (self.CY * self.r))
        costheta = math.cos(theta)
        sintheta = math.sin(theta)
        lon = self.lon0 + x / (self.CX * self.r * (1 + costheta))
        lat = math.asin((theta + sintheta * costheta + 2 * sintheta) / self.C)
        lon, lat = math.degrees(lon), math.degrees(lat)
        return lon, lat

    def scale(self, lon, lat):
        raise NotImplemented("scale is not implemented for Eckert IV")

class Stereographic(Proj):
    "Stereographic Projection for the Spherical Earth."

    def __init__(self, *args, **kwargs):
        Proj.__init__(self, *args, **kwargs)
        self.coslat0 = math.cos(self.lat0)
        self.sinlat0 = math.sin(self.lat0)

    def geo2rect(self, lon, lat):
        lon, lat = math.radians(lon), math.radians(lat)
        coslat = math.cos(lat)
        sinlat = math.sin(lat)
        coslon = math.cos(lon - self.lon0)
        sinlon = math.sin(lon - self.lon0)
        k = 2 / (1 + self.sinlat0 * sinlat + self.coslat0 * coslat * coslon)
        x = y = self.r * k
        x *= coslat * sinlon
        y *= self.coslat0 * sinlat - self.sinlat0 * coslat * coslon
        return x, y

    def rect2geo(self, x, y):
        p = math.sqrt(x*x + y*y)
        c = 2 * math.atan(p / (2 * self.r))
        cosc = math.cos(c)
        sinc = math.sin(c)
        # FIXME: In the formulas below, should it be atan or atan2?
        if self.lat0 == math.pi / 2:
            # North Polar Aspect.
            lon = self.lon0 + math.atan(x/(-y))
        elif self.lat0 == -math.pi / 2:
            # South Polar Aspect.
            lon = self.lon0 + math.atan(x/y)
        else:
            # Any other Oblique Aspect.
            den = p * self.coslat0 * cosc - y * self.sinlat0 * sinc
            lon = self.lon0 + math.atan(x * sinc / den)
        lat = math.asin(cosc * self.sinlat0 + y * sinc * self.coslat0 / p)
        lon, lat = math.degrees(lon), math.degrees(lat)
        return lon, lat

    def scale(self, lon, lat):
        raise NotImplemented("scale is not implemented for Stereographic")

class AzimuthalEquidistant(Proj):
    "Azimuthal Equidistant Projection for the Spherical Earth."

    def __init__(self, *args, **kwargs):
        Proj.__init__(self, *args, **kwargs)
        self.coslat0 = math.cos(self.lat0)
        self.sinlat0 = math.sin(self.lat0)

    def geo2rect(self, lon, lat):
        lon, lat = math.radians(lon), math.radians(lat)
        if (lon, lat) == (self.lon0, self.lat0):
            # This shortcut avoid division by zero on the k formula below.
            return 0, 0
        coslat = math.cos(lat)
        sinlat = math.sin(lat)
        coslon = math.cos(lon - self.lon0)
        sinlon = math.sin(lon - self.lon0)
        cosc = self.sinlat0 * sinlat + self.coslat0 * coslat * coslon
        c = math.acos(cosc)
        k = c / math.sin(c)
        x = y = self.r * k
        x *= coslat * sinlon
        y *= self.coslat0 * sinlat - self.sinlat0 * coslat * coslon
        return x, y

    def rect2geo(self, x, y):
        p = math.sqrt(x*x + y*y)
        c = p / self.r
        cosc = math.cos(c)
        sinc = math.sin(c)
        # FIXME: In the formulas below, should it be atan or atan2?
        if self.lat0 == math.pi / 2:
            # North Polar Aspect.
            lon = self.lon0 + math.atan(x/(-y))
        elif self.lat0 == -math.pi / 2:
            # South Polar Aspect.
            lon = self.lon0 + math.atan(x/y)
        else:
            # Any other Oblique Aspect.
            den = p * self.coslat0 * cosc - y * self.sinlat0 * sinc
            lon = self.lon0 + math.atan(x * sinc / den)
        lat = math.asin(cosc * self.sinlat0 + y * sinc * self.coslat0 / p)
        lon, lat = math.degrees(lon), math.degrees(lat)
        return lon, lat

    def scale(self, lon, lat):
        raise NotImplemented("scale is not implemented for Azimuthal Equidistant")

if __name__ == "__main__":
    p = 0
    for proj in Mercator(), EMercator(), TransMercator():
        for lat1 in range(-90, 90, 5):
            for lon1 in range(-180, 180, 5):
                try:
                    lon2, lat2 = proj.rect2geo(*proj.geo2rect(lon1, lat1))
                except ProjectionError as e:
                    print(proj)
                    print(e)
                    continue
                except:
                    print(proj, lon1, lat1)
                    raise
                try:
                    assert (round(lon1, p), round(lat1, p)) == (round(lon2, p), round(lat2, p))
                except:
                    print(proj, lon1, lat1, lon2, lat2)
                    raise